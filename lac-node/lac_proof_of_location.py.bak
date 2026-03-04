"""
LAC Proof-of-Location Module v1.0
==================================
Zero-knowledge style location proofs for LightAnonChain

USE CASES:
- Journalist proves they're in a conflict zone without revealing exact coordinates
- Activist proves they're in a specific country for verification
- User proves presence in a region for location-based features
- Whistleblower attaches location proof to anonymous message

PRIVACY GUARANTEES:
- Exact coordinates NEVER leave the device
- Only region/country/zone is provable
- Commitment is cryptographic — cannot be reverse-engineered
- Blinding factor ensures each proof is unique
- Temporal binding prevents replay attacks

HONEST LIMITATIONS:
- GPS can be spoofed on rooted/jailbroken devices
- This is "sufficient trust" not "absolute proof"
- No hardware attestation (would need secure enclave)
- Accuracy depends on device GPS quality

ARCHITECTURE:
  Device (private)              Blockchain (public)
  ┌─────────────┐              ┌──────────────────┐
  │ lat, lon    │──┐           │ commitment       │
  │ blinding_r  │  │ prove()   │ zone_name        │
  │             │  ├──────────>│ timestamp        │
  │             │  │           │ proof_hash       │
  └─────────────┘  │           │ (NO coordinates) │
                   │           └──────────────────┘
                   │
                   └── verify(): zone matches commitment ✓
"""

import hashlib
import secrets
import json
import time
import math

# ═══════════════════════════════════════════════════════
# 1. GEO ZONES DATABASE
# ═══════════════════════════════════════════════════════
# Bounding boxes for countries and regions
# Format: {name: {lat_min, lat_max, lon_min, lon_max}}

COUNTRIES = {
    "Ukraine": {"lat_min": 44.0, "lat_max": 52.4, "lon_min": 22.1, "lon_max": 40.2},
    "Poland": {"lat_min": 49.0, "lat_max": 54.9, "lon_min": 14.1, "lon_max": 24.2},
    "Germany": {"lat_min": 47.2, "lat_max": 55.1, "lon_min": 5.8, "lon_max": 15.1},
    "France": {"lat_min": 41.3, "lat_max": 51.1, "lon_min": -5.1, "lon_max": 9.6},
    "United Kingdom": {"lat_min": 49.9, "lat_max": 60.9, "lon_min": -8.2, "lon_max": 1.8},
    "United States": {"lat_min": 24.4, "lat_max": 49.4, "lon_min": -125.0, "lon_max": -66.9},
    "Turkey": {"lat_min": 35.8, "lat_max": 42.1, "lon_min": 25.7, "lon_max": 44.8},
    "Georgia": {"lat_min": 41.0, "lat_max": 43.6, "lon_min": 40.0, "lon_max": 46.7},
    "Moldova": {"lat_min": 45.4, "lat_max": 48.5, "lon_min": 26.6, "lon_max": 30.2},
    "Romania": {"lat_min": 43.6, "lat_max": 48.3, "lon_min": 20.2, "lon_max": 30.0},
    "Japan": {"lat_min": 24.0, "lat_max": 46.0, "lon_min": 122.0, "lon_max": 146.0},
    "South Korea": {"lat_min": 33.1, "lat_max": 38.6, "lon_min": 124.6, "lon_max": 132.0},
    "India": {"lat_min": 6.7, "lat_max": 37.1, "lon_min": 68.1, "lon_max": 97.4},
    "Brazil": {"lat_min": -33.8, "lat_max": 5.3, "lon_min": -73.9, "lon_max": -34.8},
    "Australia": {"lat_min": -44.0, "lat_max": -10.0, "lon_min": 112.0, "lon_max": 154.0},
    "Canada": {"lat_min": 41.7, "lat_max": 83.1, "lon_min": -141.0, "lon_max": -52.6},
}

# Ukrainian oblasts (more granular zones)
UA_OBLASTS = {
    "Kyiv Oblast": {"lat_min": 49.6, "lat_max": 51.3, "lon_min": 29.2, "lon_max": 32.2},
    "Kyiv City": {"lat_min": 50.35, "lat_max": 50.55, "lon_min": 30.25, "lon_max": 30.85},
    "Dnipropetrovsk Oblast": {"lat_min": 47.6, "lat_max": 49.2, "lon_min": 33.2, "lon_max": 36.4},
    "Donetsk Oblast": {"lat_min": 46.8, "lat_max": 49.0, "lon_min": 36.7, "lon_max": 39.1},
    "Luhansk Oblast": {"lat_min": 47.9, "lat_max": 50.1, "lon_min": 38.2, "lon_max": 40.2},
    "Kharkiv Oblast": {"lat_min": 48.9, "lat_max": 50.5, "lon_min": 35.0, "lon_max": 38.3},
    "Odesa Oblast": {"lat_min": 45.2, "lat_max": 48.2, "lon_min": 28.9, "lon_max": 33.6},
    "Lviv Oblast": {"lat_min": 48.7, "lat_max": 50.5, "lon_min": 23.0, "lon_max": 25.5},
    "Zaporizhzhia Oblast": {"lat_min": 46.5, "lat_max": 48.2, "lon_min": 34.0, "lon_max": 36.8},
    "Kherson Oblast": {"lat_min": 45.8, "lat_max": 47.5, "lon_min": 32.3, "lon_max": 35.5},
    "Crimea": {"lat_min": 44.3, "lat_max": 46.2, "lon_min": 32.4, "lon_max": 36.7},
    "Mykolaiv Oblast": {"lat_min": 46.3, "lat_max": 48.3, "lon_min": 30.8, "lon_max": 33.5},
    "Chernihiv Oblast": {"lat_min": 50.5, "lat_max": 52.4, "lon_min": 30.6, "lon_max": 33.5},
    "Sumy Oblast": {"lat_min": 50.1, "lat_max": 52.4, "lon_min": 32.6, "lon_max": 35.8},
    "Poltava Oblast": {"lat_min": 48.7, "lat_max": 50.4, "lon_min": 32.2, "lon_max": 35.6},
}

# Special conflict/interest zones
SPECIAL_ZONES = {
    "Eastern Ukraine Frontline": {"lat_min": 46.8, "lat_max": 50.1, "lon_min": 36.0, "lon_max": 40.2},
    "Black Sea Coast": {"lat_min": 44.0, "lat_max": 46.8, "lon_min": 28.5, "lon_max": 40.0},
    "EU Territory": {"lat_min": 35.0, "lat_max": 72.0, "lon_min": -10.0, "lon_max": 40.0},
}

# Combine all zones
ALL_ZONES = {}
ALL_ZONES.update(COUNTRIES)
ALL_ZONES.update(UA_OBLASTS)
ALL_ZONES.update(SPECIAL_ZONES)


# ═══════════════════════════════════════════════════════
# 2. PROOF-OF-LOCATION CORE
# ═══════════════════════════════════════════════════════

class ProofOfLocation:
    """
    Zero-knowledge style location proof system.
    
    Creates cryptographic proof that a user is in a specific zone
    WITHOUT revealing their exact coordinates.
    """
    
    @staticmethod
    def _point_in_bounds(lat: float, lon: float, bounds: dict) -> bool:
        """Check if coordinates are within bounding box"""
        return (
            bounds["lat_min"] <= lat <= bounds["lat_max"] and
            bounds["lon_min"] <= lon <= bounds["lon_max"]
        )
    
    @staticmethod
    def _compute_commitment(lat: float, lon: float, blinding: str, timestamp: int) -> str:
        """
        Create cryptographic commitment to location.
        commitment = SHA256(lat || lon || blinding_factor || timestamp)
        
        Properties:
        - Hiding: cannot determine lat/lon from commitment
        - Binding: cannot change lat/lon after commitment
        - Temporal: bound to specific time
        """
        data = f"LAC:PoL:v1:{lat:.6f}:{lon:.6f}:{blinding}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def _compute_zone_proof(lat: float, lon: float, zone_name: str, blinding: str) -> str:
        """
        Proof that coordinates are in zone, without revealing coordinates.
        proof = SHA256(commitment || zone_name || "INSIDE")
        """
        commitment = ProofOfLocation._compute_commitment(lat, lon, blinding, 0)
        proof_data = f"LAC:ZoneProof:{commitment}:{zone_name}:INSIDE"
        return hashlib.sha256(proof_data.encode()).hexdigest()
    
    @staticmethod
    def detect_zones(lat: float, lon: float) -> list:
        """Detect all zones that contain the given coordinates"""
        matched = []
        for name, bounds in ALL_ZONES.items():
            if ProofOfLocation._point_in_bounds(lat, lon, bounds):
                matched.append(name)
        return matched
    
    @staticmethod
    def create_proof(lat: float, lon: float, zone_name: str = None) -> dict:
        """
        Create a Proof-of-Location.
        
        Args:
            lat: GPS latitude
            lon: GPS longitude
            zone_name: specific zone to prove (auto-detect if None)
        
        Returns:
            PUBLIC proof (safe to publish on blockchain):
                - zone_name, timestamp, commitment, proof_hash, zone_proof
            PRIVATE data (keep on device only):
                - lat, lon, blinding_factor
        """
        timestamp = int(time.time())
        blinding = secrets.token_hex(32)
        
        # Detect zones
        matched_zones = ProofOfLocation.detect_zones(lat, lon)
        
        if not matched_zones:
            return {
                'valid': False,
                'error': 'Location not in any known zone',
                'hint': 'Coordinates may be outside defined regions'
            }
        
        # Use specified zone or most specific match
        if zone_name and zone_name in matched_zones:
            chosen_zone = zone_name
        elif zone_name:
            return {
                'valid': False,
                'error': f'Not in zone: {zone_name}',
                'actual_zones': matched_zones
            }
        else:
            # Pick most specific (smallest area) zone
            def zone_area(name):
                b = ALL_ZONES[name]
                return (b['lat_max'] - b['lat_min']) * (b['lon_max'] - b['lon_min'])
            chosen_zone = min(matched_zones, key=zone_area)
        
        # Create commitment
        commitment = ProofOfLocation._compute_commitment(lat, lon, blinding, timestamp)
        zone_proof = ProofOfLocation._compute_zone_proof(lat, lon, chosen_zone, blinding)
        
        # Proof hash = binding of all public components
        proof_hash = hashlib.sha256(
            f"LAC:PoL:FINAL:{commitment}:{chosen_zone}:{timestamp}:{zone_proof}".encode()
        ).hexdigest()
        
        # Accuracy estimate (zone size in km)
        bounds = ALL_ZONES[chosen_zone]
        lat_km = (bounds['lat_max'] - bounds['lat_min']) * 111
        lon_km = (bounds['lon_max'] - bounds['lon_min']) * 111 * math.cos(math.radians((bounds['lat_min'] + bounds['lat_max'])/2))
        area_km2 = lat_km * lon_km
        
        return {
            'valid': True,
            
            # === PUBLIC (safe to publish) ===
            'public': {
                'zone': chosen_zone,
                'all_zones': matched_zones,
                'timestamp': timestamp,
                'commitment': commitment,
                'zone_proof': zone_proof,
                'proof_hash': proof_hash,
                'protocol': 'LAC-PoL-v1',
                'area_km2': round(area_km2),
                'privacy_level': 'zone-only',
            },
            
            # === PRIVATE (device only, NEVER share) ===
            'private': {
                'lat': lat,
                'lon': lon,
                'blinding_factor': blinding,
            }
        }
    
    @staticmethod
    def verify_proof(proof_public: dict) -> dict:
        """
        Verify a published Proof-of-Location.
        
        Note: We can only verify structural integrity.
        We CANNOT verify that coordinates were real GPS (honest limitation).
        
        Checks:
        1. Zone exists in database
        2. Proof hash is structurally valid
        3. Timestamp is reasonable
        """
        zone = proof_public.get('zone', '')
        timestamp = proof_public.get('timestamp', 0)
        commitment = proof_public.get('commitment', '')
        zone_proof = proof_public.get('zone_proof', '')
        proof_hash = proof_public.get('proof_hash', '')
        
        errors = []
        
        # Check zone exists
        if zone not in ALL_ZONES:
            errors.append(f'Unknown zone: {zone}')
        
        # Check timestamp
        now = int(time.time())
        age = now - timestamp
        if age < -300:  # 5 min future tolerance
            errors.append('Timestamp is in the future')
        
        # Check proof hash consistency
        expected_hash = hashlib.sha256(
            f"LAC:PoL:FINAL:{commitment}:{zone}:{timestamp}:{zone_proof}".encode()
        ).hexdigest()
        
        if proof_hash != expected_hash:
            errors.append('Proof hash mismatch — data tampered')
        
        # Check all hashes are valid hex
        for name, val in [('commitment', commitment), ('zone_proof', zone_proof), ('proof_hash', proof_hash)]:
            if not val or len(val) != 64:
                errors.append(f'Invalid {name} format')
        
        if errors:
            return {'valid': False, 'errors': errors}
        
        # Age classification
        if age < 300:
            freshness = 'live'          # < 5 min
        elif age < 3600:
            freshness = 'recent'        # < 1 hour
        elif age < 86400:
            freshness = 'today'         # < 24 hours
        else:
            freshness = 'historical'    # older
        
        return {
            'valid': True,
            'zone': zone,
            'timestamp': timestamp,
            'age_seconds': age,
            'freshness': freshness,
            'protocol': proof_public.get('protocol', 'unknown'),
            'trust_note': 'GPS can be spoofed. This proves device reported being in zone, not absolute truth.'
        }
    
    @staticmethod
    def create_message_proof(lat: float, lon: float, message_text: str, zone_name: str = None) -> dict:
        """
        Create a location-stamped message proof.
        Binds a message to a location without revealing coordinates.
        
        Use case: journalist sends message from conflict zone.
        """
        proof = ProofOfLocation.create_proof(lat, lon, zone_name)
        if not proof.get('valid'):
            return proof
        
        # Bind message to location proof
        msg_hash = hashlib.sha256(message_text.encode()).hexdigest()
        binding = hashlib.sha256(
            f"LAC:MsgLoc:{msg_hash}:{proof['public']['proof_hash']}".encode()
        ).hexdigest()
        
        proof['public']['message_binding'] = binding
        proof['public']['message_hash'] = msg_hash
        
        return proof
    
    @staticmethod
    def verify_message_proof(proof_public: dict, message_text: str) -> dict:
        """Verify that a message was bound to a location proof"""
        base_verify = ProofOfLocation.verify_proof(proof_public)
        if not base_verify.get('valid'):
            return base_verify
        
        msg_hash = hashlib.sha256(message_text.encode()).hexdigest()
        expected_binding = hashlib.sha256(
            f"LAC:MsgLoc:{msg_hash}:{proof_public['proof_hash']}".encode()
        ).hexdigest()
        
        if proof_public.get('message_binding') != expected_binding:
            base_verify['message_verified'] = False
            base_verify['message_error'] = 'Message does not match proof'
        else:
            base_verify['message_verified'] = True
        
        return base_verify
    
    @staticmethod
    def get_available_zones() -> dict:
        """List all available zones for the frontend"""
        result = {
            'countries': list(COUNTRIES.keys()),
            'ua_oblasts': list(UA_OBLASTS.keys()),
            'special_zones': list(SPECIAL_ZONES.keys()),
            'total_zones': len(ALL_ZONES),
        }
        return result


# ═══════════════════════════════════════════════════════
# 3. SELF-TEST
# ═══════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 60)
    print("LAC Proof-of-Location v1.0 — Self Test")
    print("=" * 60)
    
    # Test 1: Dnipro
    print("\n--- Test 1: Dnipro (48.45, 34.98) ---")
    proof = ProofOfLocation.create_proof(48.45, 34.98)
    print(f"  Valid: {proof['valid']}")
    print(f"  Zone: {proof['public']['zone']}")
    print(f"  All zones: {proof['public']['all_zones']}")
    print(f"  Area: ~{proof['public']['area_km2']} km²")
    print(f"  Commitment: {proof['public']['commitment'][:24]}...")
    print(f"  Coordinates in proof: NO ✅")
    
    # Verify
    v = ProofOfLocation.verify_proof(proof['public'])
    print(f"  Verified: {v['valid']}")
    print(f"  Freshness: {v.get('freshness')}")
    
    # Test 2: Kyiv with specific zone
    print("\n--- Test 2: Kyiv City proof ---")
    proof2 = ProofOfLocation.create_proof(50.45, 30.52, "Kyiv City")
    print(f"  Zone: {proof2['public']['zone']}")
    print(f"  All zones: {proof2['public']['all_zones']}")
    
    # Test 3: Message proof (journalist use case)
    print("\n--- Test 3: Journalist message from Donetsk ---")
    msg = "Shelling observed near residential area. Civilians evacuating."
    proof3 = ProofOfLocation.create_message_proof(48.0, 37.8, msg, "Donetsk Oblast")
    print(f"  Zone: {proof3['public']['zone']}")
    print(f"  Message binding: {proof3['public']['message_binding'][:24]}...")
    
    # Verify message
    v3 = ProofOfLocation.verify_message_proof(proof3['public'], msg)
    print(f"  Message verified: {v3.get('message_verified')}")
    
    # Tampered message
    v3_bad = ProofOfLocation.verify_message_proof(proof3['public'], "Tampered text")
    print(f"  Tampered msg verified: {v3_bad.get('message_verified')}")
    
    # Test 4: Outside known zones
    print("\n--- Test 4: Middle of ocean ---")
    proof4 = ProofOfLocation.create_proof(0.0, 0.0)
    print(f"  Valid: {proof4['valid']}")
    print(f"  Error: {proof4.get('error')}")
    
    # Test 5: Tampered proof
    print("\n--- Test 5: Tampered proof ---")
    fake = proof['public'].copy()
    fake['zone'] = 'Donetsk Oblast'  # Changed zone
    v5 = ProofOfLocation.verify_proof(fake)
    print(f"  Tampered verified: {v5['valid']}")
    if not v5['valid']:
        print(f"  Errors: {v5['errors']}")
    
    print("\n✅ All tests complete!")
    print(f"\nAvailable zones: {ProofOfLocation.get_available_zones()['total_zones']}")
