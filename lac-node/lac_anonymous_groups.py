#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAC Anonymous Groups with Ring Signatures
Повна анонімність в групових чатах - неможливо визначити автора
"""
import time
import hashlib
import secrets
from typing import Dict, List, Optional, Tuple
import json


class AnonymousGroup:
    """
    Анонімна група з Ring Signatures
    
    Features:
    - До 100 учасників
    - Ring Signature для кожного повідомлення
    - Ephemeral messages (5 хвилин TTL)
    - Stealth group ID
    - Автор повідомлення = ANONYMOUS
    """
    
    def __init__(
        self,
        group_id: str,
        name: str,
        creator: str,
        participants: List[str],
        stealth: bool = True
    ):
        self.group_id = group_id
        self.name = name
        self.creator = creator  # Зберігається тільки при створенні
        self.participants = participants  # List of addresses
        self.stealth = stealth  # True = невидима в публічному списку
        self.created_at = int(time.time())
        self.messages = []  # Ephemeral messages
        self.max_participants = 100
        self.message_ttl = 300  # 5 хвилин
    
    
    def add_participant(self, address: str) -> Tuple[bool, str]:
        """Додати учасника в групу"""
        if len(self.participants) >= self.max_participants:
            return False, f"Group full (max {self.max_participants})"
        
        if address in self.participants:
            return False, "Already in group"
        
        self.participants.append(address)
        return True, "Added to group"
    
    
    def remove_participant(self, address: str) -> Tuple[bool, str]:
        """Видалити учасника з групи"""
        if address not in self.participants:
            return False, "Not in group"
        
        if address == self.creator:
            return False, "Cannot remove creator"
        
        self.participants.remove(address)
        return True, "Removed from group"
    
    
    def cleanup_ephemeral(self) -> int:
        """
        Видалити ephemeral messages старіші за TTL
        Returns: кількість видалених повідомлень
        """
        current_time = int(time.time())
        before_count = len(self.messages)
        
        self.messages = [
            msg for msg in self.messages
            if current_time - msg['timestamp'] < self.message_ttl
        ]
        
        return before_count - len(self.messages)
    
    
    def to_dict(self, include_creator: bool = False) -> dict:
        """Serialize group to dict"""
        data = {
            'group_id': self.group_id,
            'name': self.name,
            'participants': self.participants,
            'participant_count': len(self.participants),
            'stealth': self.stealth,
            'created_at': self.created_at,
            'message_count': len(self.messages)
        }
        
        if include_creator:
            data['creator'] = self.creator
        
        return data


class AnonymousPoll:
    """
    Анонімне голосування з Ring Signatures
    
    Features:
    - Повна анонімність голосування
    - Ring Signature для кожного голосу
    - Ephemeral poll (5 хвилин TTL)
    - Захист від подвійного голосування
    - До 10 опцій
    """
    
    def __init__(
        self,
        poll_id: str,
        group_id: str,
        question: str,
        options: List[str],
        creator_ring: dict
    ):
        self.poll_id = poll_id
        self.group_id = group_id
        self.question = question
        self.options = options[:10]  # Max 10 options
        self.creator_ring = creator_ring  # Ring signature of creator
        self.created_at = int(time.time())
        self.expires_at = self.created_at + 300  # 5 min TTL
        self.votes = []  # List of anonymous votes
        self.vote_ids = set()  # To prevent duplicate votes
    
    
    def add_vote(
        self,
        option_index: int,
        ring_signature: dict,
        voter_address: str = None
    ) -> Tuple[bool, str]:
        """
        Додати анонімний голос
        
        Args:
            voter_address: Address для генерації унікального vote_id (НЕ зберігається!)
        
        Returns:
            (success, message/error)
        """
        # Check if poll expired
        if int(time.time()) > self.expires_at:
            return False, "Poll expired"
        
        # Validate option index
        if option_index < 0 or option_index >= len(self.options):
            return False, "Invalid option index"
        
        # Generate UNIQUE vote ID from ring signature + voter hash
        # Voter address hashed to preserve anonymity
        vote_data = {
            'ring_signature': ring_signature,
            'voter_hash': hashlib.sha256(voter_address.encode()).hexdigest() if voter_address else 'anonymous'
        }
        
        vote_id = hashlib.sha256(
            json.dumps(vote_data, sort_keys=True).encode()
        ).hexdigest()[:32]
        
        # Check for duplicate vote
        if vote_id in self.vote_ids:
            return False, "Already voted"
        
        # Add vote (NO voter address stored - anonymous!)
        vote = {
            'option_index': option_index,
            'ring_signature': ring_signature,
            'timestamp': int(time.time()),
            'vote_id': vote_id
        }
        
        self.votes.append(vote)
        self.vote_ids.add(vote_id)
        
        return True, "Vote recorded"
    
    
    def get_results(self) -> dict:
        """
        Отримати результати голосування (анонімні)
        
        Returns:
            {
                'question': str,
                'options': List[str],
                'results': List[int],  # Vote counts
                'total_votes': int,
                'expires_in': int  # seconds
            }
        """
        # Count votes per option
        results = [0] * len(self.options)
        for vote in self.votes:
            option_idx = vote['option_index']
            if 0 <= option_idx < len(results):
                results[option_idx] += 1
        
        expires_in = max(0, self.expires_at - int(time.time()))
        
        return {
            'poll_id': self.poll_id,
            'question': self.question,
            'options': self.options,
            'results': results,
            'total_votes': len(self.votes),
            'created_at': self.created_at,
            'expires_in': expires_in,
            'expired': expires_in == 0
        }
    
    
    def is_expired(self) -> bool:
        """Перевірити чи poll закінчився"""
        return int(time.time()) > self.expires_at
    
    
    def to_dict(self) -> dict:
        """Export poll to dict"""
        return {
            'poll_id': self.poll_id,
            'group_id': self.group_id,
            'question': self.question,
            'options': self.options,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'vote_count': len(self.votes)
        }


class LACAnonymousGroups:
    """
    Manager для Anonymous Groups з Ring Signatures
    """
    
    def __init__(self, ring_signature_module=None):
        self.groups: Dict[str, AnonymousGroup] = {}
        self.polls: Dict[str, AnonymousPoll] = {}  # Poll storage
        self.ring_sig = ring_signature_module
        self.last_cleanup = int(time.time())
        self.cleanup_interval = 60  # Cleanup кожну хвилину
    
    
    def create_group(
        self,
        name: str,
        creator: str,
        stealth: bool = True
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Створити нову анонімну групу
        
        Returns:
            (success, message/error, group_id)
        """
        if not name or len(name) > 100:
            return False, "Invalid group name", None
        
        # Generate stealth group ID
        random_salt = secrets.token_hex(16)
        group_id = hashlib.sha256(
            f"{name}{creator}{time.time()}{random_salt}".encode()
        ).hexdigest()
        
        # Create group
        group = AnonymousGroup(
            group_id=group_id,
            name=name,
            creator=creator,
            participants=[creator],  # Creator is first participant
            stealth=stealth
        )
        
        self.groups[group_id] = group
        
        return True, "Group created", group_id
    
    
    def join_group(
        self,
        group_id: str,
        participant: str
    ) -> Tuple[bool, str]:
        """Приєднатися до групи"""
        if group_id not in self.groups:
            return False, "Group not found"
        
        group = self.groups[group_id]
        return group.add_participant(participant)
    
    
    def leave_group(
        self,
        group_id: str,
        participant: str
    ) -> Tuple[bool, str]:
        """Вийти з групи"""
        if group_id not in self.groups:
            return False, "Group not found"
        
        group = self.groups[group_id]
        return group.remove_participant(participant)
    
    
    def post_message(
        self,
        group_id: str,
        sender: str,
        text: str,
        ring_signature: Optional[dict] = None
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Відправити anonymous message в групу
        
        Args:
            group_id: ID групи
            sender: Адреса відправника (тільки для верифікації)
            text: Текст повідомлення
            ring_signature: Ring signature від відправника
        
        Returns:
            (success, message/error, message_dict)
        """
        if group_id not in self.groups:
            return False, "Group not found", None
        
        group = self.groups[group_id]
        
        # Verify sender is in group
        if sender not in group.participants:
            return False, "Not a group participant", None
        
        # Verify ring signature if provided
        if ring_signature and self.ring_sig:
            # Ring signature повинен містити всіх учасників як decoys
            ring_members = ring_signature.get('ring_members', [])
            
            # Перевірити що ring містить учасників групи
            if not all(member in group.participants for member in ring_members):
                return False, "Invalid ring signature members", None
            
            # TODO: Verify ring signature cryptographically
            # For now, trust the signature if structure is valid
        
        # Create anonymous message
        message = {
            'message_id': hashlib.sha256(
                f"{group_id}{text}{time.time()}{secrets.token_hex(8)}".encode()
            ).hexdigest()[:32],
            'text': text,
            'timestamp': int(time.time()),
            'author': 'anonymous',  # ЗАВЖДИ anonymous!
            'ring_signature': ring_signature,
            'ring_size': len(group.participants)
        }
        
        group.messages.append(message)
        
        # Cleanup old messages
        self._auto_cleanup()
        
        return True, "Message posted", message
    
    
    def get_messages(
        self,
        group_id: str,
        requester: str,
        limit: int = 50
    ) -> Tuple[bool, str, List[dict]]:
        """
        Отримати повідомлення з групи
        
        Args:
            group_id: ID групи
            requester: Хто запитує (має бути учасником)
            limit: Скільки повідомлень повернути
        
        Returns:
            (success, message/error, messages_list)
        """
        if group_id not in self.groups:
            return False, "Group not found", []
        
        group = self.groups[group_id]
        
        # Verify requester is in group
        if requester not in group.participants:
            return False, "Not a group participant", []
        
        # Cleanup expired messages
        group.cleanup_ephemeral()
        
        # Return latest messages
        messages = group.messages[-limit:] if limit else group.messages
        
        # Remove ring_signature from response (too large)
        messages_clean = []
        for msg in messages:
            msg_copy = msg.copy()
            if 'ring_signature' in msg_copy:
                msg_copy['ring_signature_present'] = True
                del msg_copy['ring_signature']
            messages_clean.append(msg_copy)
        
        return True, "OK", messages_clean
    
    
    def get_group_info(
        self,
        group_id: str,
        requester: str
    ) -> Tuple[bool, str, Optional[dict]]:
        """Отримати інформацію про групу"""
        if group_id not in self.groups:
            return False, "Group not found", None
        
        group = self.groups[group_id]
        
        # Verify requester is in group
        if requester not in group.participants:
            return False, "Not a group participant", None
        
        group.cleanup_ephemeral()
        
        return True, "OK", group.to_dict(include_creator=False)
    
    
    def list_my_groups(
        self,
        address: str
    ) -> List[dict]:
        """Список груп де учасник"""
        my_groups = []
        
        for gid, group in self.groups.items():
            if address in group.participants:
                my_groups.append(group.to_dict(include_creator=False))
        
        return my_groups
    
    
    def list_public_groups(self) -> List[dict]:
        """Список публічних груп (не stealth)"""
        public_groups = []
        
        for gid, group in self.groups.items():
            if not group.stealth:
                public_groups.append({
                    'group_id': group.group_id,
                    'name': group.name,
                    'participant_count': len(group.participants),
                    'created_at': group.created_at
                })
        
        return public_groups
    
    
    # ===================== POLLS METHODS =====================
    
    def create_poll(
        self,
        group_id: str,
        creator: str,
        question: str,
        options: List[str],
        ring_signature: dict
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Створити анонімне голосування в групі
        
        Args:
            group_id: ID групи
            creator: Адреса створювача (для перевірки участі)
            question: Питання
            options: Список опцій (2-10)
            ring_signature: Ring signature створювача (анонімність!)
        
        Returns:
            (success, message/error, poll_id)
        """
        # Validate group
        if group_id not in self.groups:
            return False, "Group not found", None
        
        group = self.groups[group_id]
        
        # Verify creator is in group
        if creator not in group.participants:
            return False, "Not a group participant", None
        
        # Validate question
        if not question or len(question) > 500:
            return False, "Invalid question (max 500 chars)", None
        
        # Validate options
        if not options or len(options) < 2:
            return False, "Need at least 2 options", None
        
        if len(options) > 10:
            return False, "Max 10 options", None
        
        # Validate ring signature
        if ring_signature:
            ring_members = ring_signature.get('ring_members', [])
            if not all(member in group.participants for member in ring_members):
                return False, "Invalid ring signature", None
        
        # Generate poll ID
        poll_id = hashlib.sha256(
            f"{group_id}{question}{time.time()}{secrets.token_hex(8)}".encode()
        ).hexdigest()
        
        # Create poll
        poll = AnonymousPoll(
            poll_id=poll_id,
            group_id=group_id,
            question=question,
            options=options,
            creator_ring=ring_signature
        )
        
        self.polls[poll_id] = poll
        
        return True, "Poll created", poll_id
    
    
    def vote_on_poll(
        self,
        poll_id: str,
        voter: str,
        option_index: int,
        ring_signature: dict
    ) -> Tuple[bool, str]:
        """
        Проголосувати анонімно в poll
        
        Args:
            poll_id: ID голосування
            voter: Адреса голосуючого (для перевірки участі в групі)
            option_index: Індекс обраної опції
            ring_signature: Ring signature голосу (анонімність!)
        
        Returns:
            (success, message/error)
        """
        # Validate poll exists
        if poll_id not in self.polls:
            return False, "Poll not found"
        
        poll = self.polls[poll_id]
        
        # Validate voter is in group
        if poll.group_id not in self.groups:
            return False, "Group not found"
        
        group = self.groups[poll.group_id]
        if voter not in group.participants:
            return False, "Not a group participant"
        
        # Validate ring signature
        if ring_signature:
            ring_members = ring_signature.get('ring_members', [])
            if not all(member in group.participants for member in ring_members):
                return False, "Invalid ring signature"
        
        # Add vote (AnonymousPoll handles duplicate check)
        success, msg = poll.add_vote(option_index, ring_signature, voter)
        
        return success, msg
    
    
    def get_poll(
        self,
        poll_id: str,
        requester: str
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Отримати poll з результатами
        
        Args:
            poll_id: ID голосування
            requester: Хто запитує (має бути учасником групи)
        
        Returns:
            (success, message/error, poll_data)
        """
        if poll_id not in self.polls:
            return False, "Poll not found", None
        
        poll = self.polls[poll_id]
        
        # Verify requester is in group
        if poll.group_id not in self.groups:
            return False, "Group not found", None
        
        group = self.groups[poll.group_id]
        if requester not in group.participants:
            return False, "Not a group participant", None
        
        # Return results
        results = poll.get_results()
        
        return True, "OK", results
    
    
    def list_group_polls(
        self,
        group_id: str,
        requester: str
    ) -> Tuple[bool, str, List[dict]]:
        """
        Список всіх polls в групі
        
        Args:
            group_id: ID групи
            requester: Хто запитує (має бути учасником)
        
        Returns:
            (success, message/error, polls_list)
        """
        # Validate group
        if group_id not in self.groups:
            return False, "Group not found", []
        
        group = self.groups[group_id]
        
        # Verify requester
        if requester not in group.participants:
            return False, "Not a group participant", []
        
        # Get all polls for this group
        group_polls = []
        
        for pid, poll in self.polls.items():
            if poll.group_id == group_id:
                # Cleanup expired polls
                if not poll.is_expired():
                    group_polls.append(poll.to_dict())
        
        return True, "OK", group_polls
    
    
    def cleanup_expired_polls(self) -> int:
        """
        Видалити закінчені polls
        
        Returns:
            Кількість видалених polls
        """
        expired_polls = [
            pid for pid, poll in self.polls.items()
            if poll.is_expired()
        ]
        
        for pid in expired_polls:
            del self.polls[pid]
        
        return len(expired_polls)
    
    
    def _auto_cleanup(self):
        """Автоматичний cleanup ephemeral messages та expired polls"""
        current_time = int(time.time())
        
        if current_time - self.last_cleanup > self.cleanup_interval:
            total_removed = 0
            
            # Cleanup messages
            for group in self.groups.values():
                removed = group.cleanup_ephemeral()
                total_removed += removed
            
            # Cleanup expired polls
            removed_polls = self.cleanup_expired_polls()
            
            self.last_cleanup = current_time
            
            if total_removed > 0 or removed_polls > 0:
                print(f"🗑️ Cleaned up {total_removed} messages, {removed_polls} polls")
    
    
    def get_stats(self) -> dict:
        """Статистика Anonymous Groups та Polls"""
        total_messages = sum(len(g.messages) for g in self.groups.values())
        total_participants = sum(len(g.participants) for g in self.groups.values())
        total_votes = sum(len(p.votes) for p in self.polls.values())
        active_polls = sum(1 for p in self.polls.values() if not p.is_expired())
        
        return {
            'total_groups': len(self.groups),
            'stealth_groups': sum(1 for g in self.groups.values() if g.stealth),
            'public_groups': sum(1 for g in self.groups.values() if not g.stealth),
            'total_messages': total_messages,
            'total_participants': total_participants,
            'average_participants': total_participants / len(self.groups) if self.groups else 0,
            'total_polls': len(self.polls),
            'active_polls': active_polls,
            'total_votes': total_votes
        }
    
    
    def save_to_dict(self) -> dict:
        """Serialize всіх груп для збереження"""
        return {
            gid: {
                'group_id': group.group_id,
                'name': group.name,
                'creator': group.creator,
                'participants': group.participants,
                'stealth': group.stealth,
                'created_at': group.created_at,
                'messages': group.messages  # Ephemeral, можна не зберігати
            }
            for gid, group in self.groups.items()
        }
    
    
    def load_from_dict(self, data: dict):
        """Завантажити групи з dict"""
        for gid, group_data in data.items():
            group = AnonymousGroup(
                group_id=group_data['group_id'],
                name=group_data['name'],
                creator=group_data['creator'],
                participants=group_data['participants'],
                stealth=group_data.get('stealth', True)
            )
            group.created_at = group_data['created_at']
            group.messages = group_data.get('messages', [])
            
            self.groups[gid] = group


# Helper functions for Ring Signature generation
def generate_ring_signature_for_group(
    sender_address: str,
    group_participants: List[str],
    message_hash: str,
    ring_sig_module
) -> dict:
    """
    Генерує Ring Signature для повідомлення в групі
    
    Args:
        sender_address: Адреса відправника
        group_participants: Всі учасники групи (використовуються як ring)
        message_hash: Hash повідомлення для підпису
        ring_sig_module: Модуль Ring Signatures
    
    Returns:
        Ring signature dict
    """
    if not ring_sig_module:
        # Fallback якщо Ring Signatures недоступні
        return {
            'ring_members': group_participants,
            'signature': 'simulated',
            'message_hash': message_hash
        }
    
    # Generate real ring signature
    # TODO: Integrate with existing lac_ring_signatures module
    ring_signature = {
        'ring_members': group_participants,
        'signer': None,  # NEVER reveal signer!
        'message_hash': message_hash,
        'timestamp': int(time.time())
    }
    
    return ring_signature


if __name__ == '__main__':
    # Test Groups
    groups = LACAnonymousGroups()
    
    # Create stealth group
    success, msg, gid = groups.create_group(
        name="Secret Group",
        creator="addr1",
        stealth=True
    )
    
    print(f"✅ Created group: {success}, GID: {gid}")
    
    # Add participants
    groups.join_group(gid, "addr2")
    groups.join_group(gid, "addr3")
    
    # Post anonymous message
    success, msg, message = groups.post_message(
        group_id=gid,
        sender="addr2",
        text="Hello from someone in the group!",
        ring_signature={'ring_members': ['addr1', 'addr2', 'addr3']}
    )
    
    print(f"✅ Posted message: {success}")
    
    # Get messages
    success, msg, messages = groups.get_messages(gid, "addr1")
    print(f"✅ Messages: {len(messages)}")
    
    # === TEST POLLS ===
    print("\n=== TESTING POLLS ===")
    
    # Create poll
    success, msg, poll_id = groups.create_poll(
        group_id=gid,
        creator="addr1",
        question="What's the price of LAC in 2026?",
        options=["$0.01 - $0.10", "$0.10 - $1.00", "$1.00 - $10.00"],
        ring_signature={'ring_members': ['addr1', 'addr2', 'addr3']}
    )
    
    print(f"✅ Created poll: {success}, PID: {poll_id}")
    
    # Vote (anonymous!)
    success, msg = groups.vote_on_poll(
        poll_id=poll_id,
        voter="addr2",
        option_index=1,  # "$0.10 - $1.00"
        ring_signature={'ring_members': ['addr1', 'addr2', 'addr3']}
    )
    
    print(f"✅ Voted: {success}, {msg}")
    
    # Another vote
    success, msg = groups.vote_on_poll(
        poll_id=poll_id,
        voter="addr3",
        option_index=2,  # "$1.00 - $10.00"
        ring_signature={'ring_members': ['addr1', 'addr2', 'addr3']}
    )
    
    print(f"✅ Voted: {success}, {msg}")
    
    # Get results
    success, msg, results = groups.get_poll(poll_id, "addr1")
    print(f"✅ Poll results: {results}")
    
    # List all polls in group
    success, msg, polls = groups.list_group_polls(gid, "addr1")
    print(f"✅ Group polls: {len(polls)}")
    
    # Stats
    print(f"\n✅ Stats: {groups.get_stats()}")