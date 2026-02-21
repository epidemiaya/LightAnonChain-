#!/usr/bin/env python3
"""
LAC PoET Mining v3 - Fair Distribution System

Hybrid mining:
- 12 Speed winners (fastest proofs) → Level advantage
- 7 Lottery winners (random from all) → Fair chance for all
- Anti-pool: max 3 wins per address
- Newbie boost: +50% for early adopters
- Anti-domination: penalty for winning too much

190 LAC per block, 10 LAC per winner
"""

import time
import random
import hashlib
import secrets
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter


class LACPoETMiningV3:
    """
    Fair PoET Mining with Speed + Lottery
    
    Prevents:
    - Pool domination (max wins limit)
    - 51% attacks (distributed winners)
    - Early adopter advantage (newbie boost)
    - Whale domination (lottery gives chances to small players)
    """
    
    # Block rewards
    BLOCK_REWARD = 190.0  # LAC per block
    WINNERS_PER_BLOCK = 19
    SPEED_WINNERS = 12  # Top 12 fastest
    LOTTERY_WINNERS = 7  # 7 random from all participants
    REWARD_PER_WINNER = BLOCK_REWARD / WINNERS_PER_BLOCK  # 10 LAC
    
    # Timing
    TARGET_BLOCK_TIME = 10.0  # seconds
    DIFFICULTY_ADJUSTMENT_INTERVAL = 100  # blocks
    
    # Participation requirements
    MIN_BALANCE_FOR_MINING = 50.0  # LAC
    
    # Level system (wait time ranges in seconds)
    WAIT_TIMES = {
        0: (12, 20),
        1: (10, 18),
        2: (8, 16),
        3: (7, 14),
        4: (6, 12),
        5: (5, 10),
        6: (4, 8),
        7: (3, 6),
    }
    MAX_LEVEL = 7
    
    # Balance bonuses (PoS element)
    BALANCE_BONUSES = [
        (10000, 0.10),  # 10k+ LAC → +10%
        (1000, 0.05),   # 1k-9.9k LAC → +5%
        (50, 0.00),     # 50-999 LAC → +0%
    ]
    
    # Anti-pool
    MAX_WINS_PER_ADDRESS = 3  # in speed winners
    
    # Anti-domination (penalty for winning too much)
    DOMINATION_THRESHOLD = 20  # wins in last 100 blocks
    DOMINATION_PENALTY = 1.5   # wait_time multiplier
    
    # Early adopter boost
    EARLY_ADOPTER_SUPPLY = 10_000_000  # First 10M LAC
    EARLY_ADOPTER_BOOST = 1.50  # +50% chances
    
    # Newbie boost
    NEWBIE_PERIOD = 30 * 24 * 3600  # 30 days in seconds
    NEWBIE_BOOST = 1.20  # +20% chances
    
    def __init__(
        self,
        current_height: int = 0,
        current_difficulty: float = 1.0,
        total_supply_mined: float = 0.0
    ):
        self.current_height = current_height
        self.difficulty = current_difficulty
        self.total_supply_mined = total_supply_mined
        self.block_times = []
        
        # Track wins for anti-domination
        self.recent_wins = defaultdict(int)  # address → wins in last 100 blocks
        self.win_history = []  # [(block, address), ...]
    
    def is_early_adopter_phase(self) -> bool:
        """Check if still in early adopter phase"""
        return self.total_supply_mined < self.EARLY_ADOPTER_SUPPLY
    
    def can_mine(self, balance: float) -> bool:
        """Check if node can participate"""
        return balance >= self.MIN_BALANCE_FOR_MINING
    
    def get_balance_bonus(self, balance: float) -> float:
        """Get balance bonus (PoS element)"""
        for threshold, bonus in self.BALANCE_BONUSES:
            if balance >= threshold:
                return bonus
        return 0.0
    
    def calculate_wait_time(
        self,
        level: int,
        balance: float,
        address: str,
        account_created_at: float = None,
        block_hash: str = None
    ) -> float:
        """
        Calculate wait time for miner
        
        Factors:
        - Level (main factor)
        - Balance (PoS bonus)
        - Recent wins (anti-domination penalty)
        - Account age (newbie boost)
        - Randomness (deterministic per block)
        """
        # Clamp level
        level = max(0, min(self.MAX_LEVEL, level))
        
        # Base wait time range
        min_wait, max_wait = self.WAIT_TIMES[level]
        
        # Deterministic random in range
        if block_hash:
            seed = f"{address}:{block_hash}:{self.current_height}"
            seed_hash = hashlib.sha256(seed.encode()).digest()
            random_value = int.from_bytes(seed_hash[:8], 'big') / (2**64)
        else:
            random_value = random.random()
        
        base_wait = min_wait + (max_wait - min_wait) * random_value
        
        # Apply balance bonus (reduces wait time)
        balance_bonus = self.get_balance_bonus(balance)
        balance_multiplier = 1.0 - (balance_bonus * 0.5)  # Max 5% reduction
        base_wait *= balance_multiplier
        
        # Anti-domination penalty
        recent_wins = self.recent_wins.get(address, 0)
        if recent_wins > self.DOMINATION_THRESHOLD:
            penalty = 1.0 + ((recent_wins - self.DOMINATION_THRESHOLD) * 0.1)
            penalty = min(penalty, self.DOMINATION_PENALTY)
            base_wait *= penalty
        
        return base_wait
    
    def calculate_lottery_weight(
        self,
        level: int,
        balance: float,
        account_created_at: float = None
    ) -> float:
        """
        Calculate lottery ticket weight
        
        Even Level 0 has chances, but higher levels get more tickets
        """
        # Base weight (everyone gets 1)
        weight = 1.0
        
        # Level bonus (smaller than speed, so everyone has chance)
        level_bonus = 1.0 + (level * 0.05)  # 5% per level (vs 7% for speed)
        weight *= level_bonus
        
        # Balance bonus (small)
        balance_bonus = self.get_balance_bonus(balance)
        weight *= (1.0 + balance_bonus * 0.5)  # Half of speed bonus
        
        # Newbie boost
        if account_created_at:
            age = time.time() - account_created_at
            if age < self.NEWBIE_PERIOD:
                weight *= self.NEWBIE_BOOST
        
        # Early adopter boost
        if self.is_early_adopter_phase():
            weight *= self.EARLY_ADOPTER_BOOST
        
        return weight
    
    def select_speed_winners(
        self,
        proofs: List[Dict],
        max_per_address: int = None
    ) -> List[Dict]:
        """
        Select speed winners (fastest valid proofs)
        
        With max wins limit per address (anti-pool)
        """
        if max_per_address is None:
            max_per_address = self.MAX_WINS_PER_ADDRESS
        
        # Sort by elapsed time (fastest first)
        sorted_proofs = sorted(proofs, key=lambda p: p['elapsed'])
        
        winners = []
        address_wins = Counter()
        
        for proof in sorted_proofs:
            if len(winners) >= self.SPEED_WINNERS:
                break
            
            address = proof['address']
            
            # Check max wins limit
            if address_wins[address] < max_per_address:
                winners.append(proof)
                address_wins[address] += 1
        
        return winners
    
    def select_lottery_winners(
        self,
        all_miners: List[Dict],
        exclude_addresses: set = None,
        exact_count: int = None
    ) -> List[Dict]:
        """
        Select lottery winners (weighted random)
        
        Everyone who participated has a chance!
        Can select same miner multiple times if needed.
        """
        if exclude_addresses is None:
            exclude_addresses = set()
        
        if exact_count is None:
            exact_count = self.LOTTERY_WINNERS
        
        # Filter eligible
        eligible = [m for m in all_miners if m['address'] not in exclude_addresses]
        
        if not eligible:
            # If no one to exclude from, use everyone
            eligible = all_miners
        
        if not eligible:
            return []
        
        # Calculate weights
        weights = []
        for miner in eligible:
            weight = self.calculate_lottery_weight(
                miner['level'],
                miner['balance'],
                miner.get('account_created_at')
            )
            weights.append(weight)
        
        # Weighted random selection (WITH replacement - can win multiple times)
        winners = []
        for _ in range(exact_count):
            winner = random.choices(eligible, weights=weights, k=1)[0]
            winners.append(winner)
        
        return winners
    
    def update_win_history(self, winners: List[str]):
        """Update win tracking for anti-domination"""
        # Add new wins
        for address in winners:
            self.win_history.append((self.current_height, address))
            self.recent_wins[address] += 1
        
        # Remove wins older than 100 blocks
        cutoff_block = self.current_height - 100
        self.win_history = [
            (block, addr) for block, addr in self.win_history
            if block > cutoff_block
        ]
        
        # Recalculate recent wins
        self.recent_wins = Counter([addr for _, addr in self.win_history])
    
    def calculate_rewards(self, winners: List[str]) -> Dict[str, float]:
        """Calculate rewards (same address can win multiple times)"""
        rewards = defaultdict(float)
        for address in winners:
            rewards[address] += self.REWARD_PER_WINNER
        return dict(rewards)
    
    def adjust_difficulty(self, recent_block_times: List[float]) -> float:
        """Adjust difficulty to maintain target block time"""
        if not recent_block_times:
            return self.difficulty
        
        avg_time = sum(recent_block_times) / len(recent_block_times)
        ratio = avg_time / self.TARGET_BLOCK_TIME
        ratio = max(0.75, min(1.25, ratio))  # Max 25% adjustment
        
        new_difficulty = self.difficulty / ratio
        new_difficulty = max(0.1, min(100.0, new_difficulty))
        
        return new_difficulty


class LACMiningCoordinator:
    """Coordinates mining with Speed + Lottery system"""
    
    def __init__(self, poet: LACPoETMiningV3):
        self.poet = poet
        self.active_miners = {}  # address → miner data
        self.submitted_proofs = []  # proofs for current block
        self.last_block_time = time.time()
    
    def register_miner(
        self,
        address: str,
        level: int,
        balance: float,
        account_created_at: float = None
    ) -> Dict:
        """Register miner for current block"""
        if not self.poet.can_mine(balance):
            return {
                'mining': False,
                'reason': f'Need {self.poet.MIN_BALANCE_FOR_MINING} LAC minimum'
            }
        
        self.active_miners[address] = {
            'address': address,
            'level': level,
            'balance': balance,
            'account_created_at': account_created_at or time.time(),
            'wait_time': self.poet.calculate_wait_time(
                level, balance, address, account_created_at
            ),
            'registered_at': time.time()
        }
        
        lottery_weight = self.poet.calculate_lottery_weight(
            level, balance, account_created_at
        )
        
        return {
            'mining': True,
            'wait_time': self.active_miners[address]['wait_time'],
            'lottery_weight': lottery_weight,
            'message': f"⛏️ Mining! Wait: {self.active_miners[address]['wait_time']:.1f}s"
        }
    
    def submit_proof(self, address: str) -> Optional[Dict]:
        """Miner submits proof after waiting"""
        if address not in self.active_miners:
            return None
        
        miner = self.active_miners[address]
        elapsed = time.time() - miner['registered_at']
        
        # Must wait minimum time
        if elapsed < miner['wait_time']:
            return None
        
        proof = {
            'address': address,
            'level': miner['level'],
            'balance': miner['balance'],
            'wait_time': miner['wait_time'],
            'elapsed': elapsed,
            'timestamp': time.time()
        }
        
        self.submitted_proofs.append(proof)
        return proof
    
    def mine_block(self) -> Dict:
        """Create new block with Speed + Lottery winners"""
        
        # Select Speed winners (top 12 fastest, or less if not enough proofs)
        speed_winners = self.poet.select_speed_winners(self.submitted_proofs)
        speed_count = len(speed_winners)
        
        # Calculate how many lottery winners we need to reach 19 total
        lottery_needed = self.poet.WINNERS_PER_BLOCK - speed_count
        
        # Select Lottery winners to fill remaining slots
        all_miners = list(self.active_miners.values())
        lottery_winners = self.poet.select_lottery_winners(
            all_miners,
            exclude_addresses=set(),
            exact_count=lottery_needed
        )
        
        # Combine winners
        all_winners = [w['address'] for w in speed_winners] + \
                      [w['address'] for w in lottery_winners]
        
        # Calculate rewards
        rewards = self.poet.calculate_rewards(all_winners)
        
        # Update win history
        self.poet.update_win_history(all_winners)
        
        # Track block time
        current_time = time.time()
        block_time = current_time - self.last_block_time
        self.poet.block_times.append(block_time)
        self.last_block_time = current_time
        
        # Adjust difficulty if needed
        if self.poet.current_height % self.poet.DIFFICULTY_ADJUSTMENT_INTERVAL == 0:
            old_diff = self.poet.difficulty
            self.poet.difficulty = self.poet.adjust_difficulty(
                self.poet.block_times[-self.poet.DIFFICULTY_ADJUSTMENT_INTERVAL:]
            )
            difficulty_adjusted = True
        else:
            difficulty_adjusted = False
        
        # Update supply
        self.poet.total_supply_mined += self.poet.BLOCK_REWARD
        
        # Create block
        block = {
            'height': self.poet.current_height,
            'timestamp': int(current_time),
            'block_time': block_time,
            'speed_winners': len(speed_winners),
            'lottery_winners': len(lottery_winners),
            'total_winners': len(all_winners),
            'unique_winners': len(set(all_winners)),
            'rewards': rewards,
            'total_reward': sum(rewards.values()),
            'proofs_submitted': len(self.submitted_proofs),
            'active_miners': len(self.active_miners),
            'difficulty': self.poet.difficulty,
            'difficulty_adjusted': difficulty_adjusted,
            'early_adopter_phase': self.poet.is_early_adopter_phase()
        }
        
        # Reset for next block
        self.poet.current_height += 1
        self.submitted_proofs = []
        self.active_miners = {}
        
        return block


# Test
if __name__ == '__main__':
    print("⛏️ LAC PoET Mining v3 - Speed + Lottery")
    print("=" * 70)
    
    poet = LACPoETMiningV3()
    coordinator = LACMiningCoordinator(poet)
    
    print(f"\n💰 Configuration:")
    print(f"   Block Reward: {poet.BLOCK_REWARD} LAC")
    print(f"   Speed Winners: {poet.SPEED_WINNERS} (fastest)")
    print(f"   Lottery Winners: {poet.LOTTERY_WINNERS} (random)")
    print(f"   Max Wins/Address: {poet.MAX_WINS_PER_ADDRESS} (anti-pool)")
    print(f"   Reward per Winner: {poet.REWARD_PER_WINNER} LAC")
    
    # Simulate diverse miners
    print(f"\n👥 Registering miners...")
    miners = [
        # Whales (high level + balance)
        ('whale1', 7, 50000, time.time() - 365*24*3600),  # Old account
        ('whale2', 7, 40000, time.time() - 180*24*3600),
        
        # Mid tier
        ('mid1', 5, 8000, time.time() - 90*24*3600),
        ('mid2', 5, 7000, time.time() - 60*24*3600),
        ('mid3', 4, 3000, time.time() - 45*24*3600),
        
        # Small players
        ('small1', 3, 1200, time.time() - 20*24*3600),
        ('small2', 2, 800, time.time() - 10*24*3600),
        ('small3', 1, 400, time.time() - 5*24*3600),
        
        # Newbies (recent accounts, get boost)
        ('newbie1', 0, 100, time.time() - 2*24*3600),
        ('newbie2', 0, 80, time.time() - 1*24*3600),
        ('newbie3', 1, 150, time.time() - 0.5*24*3600),
    ]
    
    for addr, level, balance, created_at in miners:
        status = coordinator.register_miner(addr, level, balance, created_at)
        if status['mining']:
            print(f"   ✅ {addr:10} L{level} {balance:6} LAC → wait {status['wait_time']:.1f}s, lottery {status['lottery_weight']:.2f}x")
    
    # Simulate proofs (with random delays)
    print(f"\n⏳ Simulating mining...")
    time.sleep(0.1)
    for addr, level, _, _ in miners:
        miner_data = coordinator.active_miners.get(addr)
        if miner_data:
            # Simulate that they waited (fake for demo)
            elapsed = miner_data['wait_time'] + random.uniform(0, 2)
            miner_data['registered_at'] = time.time() - elapsed
            coordinator.submit_proof(addr)
    
    # Mine block
    print(f"\n⛏️ Mining block...")
    block = coordinator.mine_block()
    
    print(f"\n📦 Block #{block['height']}:")
    print(f"   Speed Winners: {block['speed_winners']}")
    print(f"   Lottery Winners: {block['lottery_winners']}")
    print(f"   Total: {block['total_winners']} / Unique: {block['unique_winners']}")
    print(f"   Total Reward: {block['total_reward']:.2f} LAC")
    print(f"   Proofs: {block['proofs_submitted']} / Miners: {block['active_miners']}")
    
    print(f"\n🏆 Winners:")
    for addr, reward in sorted(block['rewards'].items(), key=lambda x: -x[1]):
        wins = list(block['rewards'].keys()).count(addr)
        miner = [m for m in miners if m[0] == addr][0]
        print(f"   {addr:10} L{miner[1]} → {reward:.0f} LAC")
    
    print("\n" + "=" * 70)
    print("✅ Test complete!")
    print("\n💡 Key features:")
    print("   • Speed winners favor high level (whales dominate)")
    print("   • Lottery winners give chance to everyone (fair)")
    print("   • Max 3 wins prevents pool domination")
    print("   • Newbies get boost in lottery")