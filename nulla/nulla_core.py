"""
Nulla — Bitcoin Light Wallet
nulla_core.py — HD wallet engine

BIP39  mnemonic generation & validation
BIP32  secp256k1 key derivation (hardened + normal)
BIP44  m/44'/0'/account'/change/index  → Legacy P2PKH
BIP84  m/84'/0'/account'/change/index  → Native SegWit P2WPKH
Keystore: AES-256-GCM + PBKDF2-SHA256 × 600k + HMAC-SHA256 MAC
"""

import os
import json
import hmac as _hmac
import hashlib
import secrets
import struct
import time
from typing import Optional, List, Dict, Tuple, Any
from pathlib import Path
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag
import coincurve

try:
    from mnemonic import Mnemonic
    HAS_MNEMONIC = True
except ImportError:
    HAS_MNEMONIC = False

import base58

NULLA_VERSION     = "1.0.0"
KEYSTORE_VERSION  = 1
PBKDF2_ITERATIONS = 600_000
SECP256K1_ORDER   = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# ── Exceptions ────────────────────────────────────────────────────────────────

class NullaError(Exception): pass
class KeystoreError(NullaError): pass
class WalletError(NullaError): pass
class CryptoError(NullaError): pass


# ── Hashing helpers ───────────────────────────────────────────────────────────

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def dsha256(data: bytes) -> bytes:
    return sha256(sha256(data))

def hash160(data: bytes) -> bytes:
    return hashlib.new("ripemd160", sha256(data)).digest()

def base58check_encode(payload: bytes) -> str:
    checksum = dsha256(payload)[:4]
    return base58.b58encode(payload + checksum).decode()

def base58check_decode(addr: str) -> bytes:
    raw = base58.b58decode(addr)
    payload, chk = raw[:-4], raw[-4:]
    if dsha256(payload)[:4] != chk:
        raise WalletError(f"Bad Base58Check checksum: {addr}")
    return payload


# ── Bech32 (BIP173) ───────────────────────────────────────────────────────────

BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32_GENERATOR = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]

def _bech32_polymod(values: List[int]) -> int:
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            chk ^= _BECH32_GENERATOR[i] if ((b >> i) & 1) else 0
    return chk

def _bech32_hrp_expand(hrp: str) -> List[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def _bech32_create_checksum(hrp: str, data: List[int]) -> List[int]:
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

def _convertbits(data: bytes, frombits: int, tobits: int, pad: bool = True) -> List[int]:
    acc, bits, ret, maxv = 0, 0, [], (1 << tobits) - 1
    for value in data:
        acc = ((acc << frombits) | value) & 0xFFFFFFFF
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (tobits - bits)) & maxv)
    return ret

def bech32_encode(hrp: str, witver: int, witprog: bytes) -> str:
    data = [witver] + _convertbits(witprog, 8, 5)
    checksum = _bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join(BECH32_CHARSET[d] for d in data + checksum)

def bech32_decode(addr: str) -> Tuple[str, int, bytes]:
    """Returns (hrp, witness_version, witness_program)."""
    addr_lower = addr.lower()
    if addr_lower != addr and addr.upper() != addr:
        raise WalletError("Mixed case bech32 address")
    pos = addr_lower.rfind("1")
    if pos < 1 or pos + 7 > len(addr_lower):
        raise WalletError("Invalid bech32 address")
    hrp = addr_lower[:pos]
    data = [BECH32_CHARSET.find(x) for x in addr_lower[pos+1:]]
    if any(d == -1 for d in data):
        raise WalletError("Invalid bech32 character")
    if _bech32_polymod(_bech32_hrp_expand(hrp) + data) != 1:
        raise WalletError("Invalid bech32 checksum")
    decoded = _convertbits(bytes(data[1:-6]), 5, 8, False)
    return hrp, data[0], bytes(decoded)


# ── secp256k1 helpers ─────────────────────────────────────────────────────────

def _pubkey(privkey_bytes: bytes, compressed: bool = True) -> bytes:
    return coincurve.PublicKey.from_valid_secret(privkey_bytes).format(compressed=compressed)

def _sign_ecdsa(privkey_bytes: bytes, msg_hash: bytes) -> bytes:
    """DER-encoded ECDSA signature (low-S, BIP62)."""
    key = coincurve.PrivateKey(privkey_bytes)
    # coincurve signs with low-S by default (RFC6979 deterministic)
    sig = key.sign(msg_hash, hasher=None)
    return sig

def _ecdh(privkey_bytes: bytes, pubkey_bytes: bytes) -> bytes:
    """ECDH shared secret."""
    pub = coincurve.PublicKey(pubkey_bytes)
    priv = coincurve.PrivateKey(privkey_bytes)
    return priv.ecdh(pub.format(compressed=False)[1:])


# ── BIP32 key derivation ──────────────────────────────────────────────────────

def _hmac_sha512(key: bytes, data: bytes) -> bytes:
    return _hmac.new(key, data, hashlib.sha512).digest()

def bip32_master(seed: bytes) -> Tuple[bytes, bytes]:
    """BIP32 master key from seed. Returns (private_key, chain_code)."""
    I = _hmac_sha512(b"Bitcoin seed", seed)
    return I[:32], I[32:]

def bip32_child(parent_key: bytes, parent_chain: bytes,
                index: int, hardened: bool = False) -> Tuple[bytes, bytes]:
    """Derive BIP32 child key."""
    if hardened:
        data = b"\x00" + parent_key + struct.pack(">I", index | 0x80000000)
    else:
        data = _pubkey(parent_key) + struct.pack(">I", index)
    I = _hmac_sha512(parent_chain, data)
    child_int = (int.from_bytes(I[:32], "big") + int.from_bytes(parent_key, "big")) % SECP256K1_ORDER
    if child_int == 0:
        raise WalletError("BIP32: derived key is zero (astronomically unlikely)")
    return child_int.to_bytes(32, "big"), I[32:]

def derive_path(seed: bytes, path: str) -> bytes:
    """
    Derive private key at BIP32 path from seed.
    Example paths:
      m/44'/0'/0'/0/0   → Legacy P2PKH
      m/84'/0'/0'/0/0   → Native SegWit P2WPKH
    """
    key, chain = bip32_master(seed)
    for part in path.replace("m/", "").split("/"):
        if not part:
            continue
        hardened = part.endswith("'")
        index = int(part.rstrip("'"))
        key, chain = bip32_child(key, chain, index, hardened=hardened)
    return key


# ── Bitcoin address types ─────────────────────────────────────────────────────

MAINNET_P2PKH_VERSION  = b"\x00"
MAINNET_P2SH_VERSION   = b"\x05"
TESTNET_P2PKH_VERSION  = b"\x6f"
TESTNET_P2SH_VERSION   = b"\xc4"


class BitcoinAddress:
    """
    Represents a Bitcoin address + its derivation info.
    Supports Legacy (P2PKH) and Native SegWit (P2WPKH).
    """

    def __init__(self, privkey: bytes, addr_type: str = "p2wpkh",
                 network: str = "mainnet", path: str = ""):
        self.privkey  = privkey
        self.pubkey   = _pubkey(privkey)
        self.addr_type = addr_type
        self.network  = network
        self.path     = path
        self._address = self._compute_address()

    def _compute_address(self) -> str:
        h160 = hash160(self.pubkey)
        if self.addr_type == "p2wpkh":
            hrp = "bc" if self.network == "mainnet" else "tb"
            return bech32_encode(hrp, 0, h160)
        elif self.addr_type == "p2pkh":
            ver = MAINNET_P2PKH_VERSION if self.network == "mainnet" else TESTNET_P2PKH_VERSION
            return base58check_encode(ver + h160)
        elif self.addr_type == "p2sh-p2wpkh":
            # BIP49: P2SH wrapping P2WPKH — "3..." address
            # redeemScript = OP_0 PUSH20 <hash160(pubkey)>
            redeem = bytes([0x00, 0x14]) + h160
            script_hash = hash160(redeem)
            ver = MAINNET_P2SH_VERSION if self.network == "mainnet" else TESTNET_P2SH_VERSION
            return base58check_encode(ver + script_hash)
        else:
            raise WalletError(f"Unknown address type: {self.addr_type}")

    @property
    def address(self) -> str:
        return self._address

    @property
    def redeem_script(self) -> Optional[bytes]:
        """P2SH redeemScript (only for p2sh-p2wpkh)."""
        if self.addr_type == "p2sh-p2wpkh":
            return bytes([0x00, 0x14]) + hash160(self.pubkey)
        return None

    @property
    def script_pubkey(self) -> bytes:
        h160 = hash160(self.pubkey)
        if self.addr_type == "p2wpkh":
            return bytes([0x00, 0x14]) + h160  # OP_0 PUSH20 <hash160>
        elif self.addr_type == "p2pkh":
            return bytes([0x76, 0xa9, 0x14]) + h160 + bytes([0x88, 0xac])
        elif self.addr_type == "p2sh-p2wpkh":
            # P2SH scriptPubKey: OP_HASH160 <hash160(redeemScript)> OP_EQUAL
            redeem = bytes([0x00, 0x14]) + h160
            sh = hash160(redeem)
            return bytes([0xa9, 0x14]) + sh + bytes([0x87])
        raise WalletError("Unknown type")

    @property
    def electrum_scripthash(self) -> str:
        """Reversed SHA256 of scriptpubkey — used in ElectrumX protocol."""
        return sha256(self.script_pubkey)[::-1].hex()

    def sign_hash(self, hash32: bytes) -> bytes:
        return _sign_ecdsa(self.privkey, hash32)

    def to_dict(self) -> dict:
        return {
            "address":    self.address,
            "pubkey":     self.pubkey.hex(),
            "type":       self.addr_type,
            "path":       self.path,
            "scripthash": self.electrum_scripthash,
        }

    def wipe(self):
        self.privkey = b"\x00" * 32


# ── HD Wallet ─────────────────────────────────────────────────────────────────

class NullaWallet:
    """
    Bitcoin HD wallet.
    Derives accounts via BIP44 (Legacy) and BIP84 (Native SegWit).
    Keystore encrypted with AES-256-GCM + PBKDF2 × 600k.
    """

    # Default: 5 receiving + 5 change addresses per account per type
    DEFAULT_GAP = 5

    def __init__(self):
        self._seed:     Optional[bytes] = None
        self._mnemonic: Optional[str]   = None
        self._unlocked: bool            = False
        self.network:   str             = "mainnet"
        self._addrs:    Dict[str, BitcoinAddress] = {}  # path → address
        self.metadata:  Dict[str, Any]  = {}

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def generate(cls, password: str, network: str = "mainnet",
                 words: int = 24) -> "NullaWallet":
        w = cls()
        w.network = network
        if HAS_MNEMONIC:
            mnemo = Mnemonic("english")
            w._mnemonic = mnemo.generate(strength=256 if words >= 24 else 128)
            w._seed     = Mnemonic.to_seed(w._mnemonic, passphrase="")
        else:
            w._seed     = secrets.token_bytes(64)
            w._mnemonic = w._seed.hex()
        w._derive_addresses()
        w._unlocked = True
        w.metadata  = {
            "created": datetime.utcnow().isoformat() + "Z",
            "network": network,
            "version": NULLA_VERSION,
            "has_bip39": HAS_MNEMONIC,
        }
        return w

    @classmethod
    def from_mnemonic(cls, mnemonic: str, password: str,
                      network: str = "mainnet") -> "NullaWallet":
        w = cls()
        w.network   = network
        mnemonic    = " ".join(mnemonic.strip().split())
        if HAS_MNEMONIC:
            mnemo = Mnemonic("english")
            if not mnemo.check(mnemonic):
                raise WalletError("Invalid BIP39 mnemonic (checksum failed)")
            w._seed = Mnemonic.to_seed(mnemonic, passphrase="")
        else:
            try:
                w._seed = bytes.fromhex(mnemonic)
            except ValueError:
                raise WalletError("Invalid mnemonic")
        w._mnemonic = mnemonic
        w._derive_addresses()
        w._unlocked = True
        w.metadata  = {
            "restored": datetime.utcnow().isoformat() + "Z",
            "network": network,
            "version": NULLA_VERSION,
        }
        return w

    # ── Key derivation ────────────────────────────────────────────────────────

    def _path(self, purpose: int, account: int, change: int, index: int) -> str:
        return f"m/{purpose}'/0'/{account}'/{change}/{index}"

    def _derive_addresses(self, gap: int = None):
        """
        Derive receiving (change=0) and change (change=1) addresses.
        Three formats: BIP84 (p2wpkh), BIP49 (p2sh-p2wpkh), BIP44 (p2pkh).
        """
        if self._seed is None:
            raise WalletError("No seed")
        gap = gap or self.DEFAULT_GAP
        for account in range(1):
            for change in range(2):
                for idx in range(gap):
                    # BIP84 — Native SegWit bc1q... (preferred)
                    p84 = self._path(84, account, change, idx)
                    if p84 not in self._addrs:
                        priv = derive_path(self._seed, p84)
                        self._addrs[p84] = BitcoinAddress(priv, "p2wpkh", self.network, p84)
                    # BIP49 — P2SH-SegWit 3... (compatible)
                    p49 = self._path(49, account, change, idx)
                    if p49 not in self._addrs:
                        priv = derive_path(self._seed, p49)
                        self._addrs[p49] = BitcoinAddress(priv, "p2sh-p2wpkh", self.network, p49)
                    # BIP44 — Legacy 1... (old)
                    p44 = self._path(44, account, change, idx)
                    if p44 not in self._addrs:
                        priv = derive_path(self._seed, p44)
                        self._addrs[p44] = BitcoinAddress(priv, "p2pkh", self.network, p44)

    def derive_more(self, gap: int):
        self._require_unlocked()
        self._derive_addresses(gap)

    def _require_unlocked(self):
        if not self._unlocked:
            raise WalletError("Wallet is locked")

    # ── Address accessors ─────────────────────────────────────────────────────

    def default_address(self, addr_type: str = "p2wpkh") -> BitcoinAddress:
        self._require_unlocked()
        purpose = 84 if addr_type == "p2wpkh" else 44
        path = self._path(purpose, 0, 0, 0)
        return self._addrs[path]

    def receiving_addresses(self, addr_type: str = "p2wpkh") -> List[BitcoinAddress]:
        self._require_unlocked()
        purpose = 84 if addr_type == "p2wpkh" else 44
        return [
            self._addrs[self._path(purpose, 0, 0, i)]
            for i in range(self.DEFAULT_GAP)
            if self._path(purpose, 0, 0, i) in self._addrs
        ]

    def change_address(self, addr_type: str = "p2wpkh") -> BitcoinAddress:
        """Internal change address (index 0 of change=1)."""
        self._require_unlocked()
        purpose = 84 if addr_type == "p2wpkh" else 44
        return self._addrs[self._path(purpose, 0, 1, 0)]

    def all_addresses(self) -> List[BitcoinAddress]:
        self._require_unlocked()
        return list(self._addrs.values())

    def find_address(self, addr: str) -> Optional[BitcoinAddress]:
        """Find BitcoinAddress object by address string."""
        self._require_unlocked()
        for a in self._addrs.values():
            if a.address == addr:
                return a
        return None

    @property
    def mnemonic(self) -> Optional[str]:
        self._require_unlocked()
        return self._mnemonic

    @property
    def address(self) -> str:
        """Primary receiving address (Native SegWit)."""
        return self.default_address("p2wpkh").address

    def all_accounts_summary(self) -> List[dict]:
        """All addresses grouped by type with labels."""
        self._require_unlocked()
        TYPE_META = {
            "p2wpkh":      {"label": "Native SegWit",  "prefix": "bc1q", "bip": "BIP84"},
            "p2sh-p2wpkh": {"label": "P2SH-SegWit",    "prefix": "3",    "bip": "BIP49"},
            "p2pkh":       {"label": "Legacy",          "prefix": "1",    "bip": "BIP44"},
        }
        seen: Dict[str, list] = {}
        for path, addr in self._addrs.items():
            t = addr.addr_type
            if t not in seen:
                seen[t] = []
            # Mark change addresses
            is_change = "/1/" in path
            d = addr.to_dict()
            d["is_change"] = is_change
            seen[t].append(d)
        return [
            {
                "type": t,
                **TYPE_META.get(t, {"label": t, "prefix": "", "bip": ""}),
                "addresses": v,
            }
            for t, v in seen.items()
        ]

    def receiving_addresses_all_types(self) -> List["BitcoinAddress"]:
        """All receiving addresses across all types — for gap limit scanning."""
        self._require_unlocked()
        return [
            a for path, a in self._addrs.items()
            if "/0/" in path  # change=0 = receiving
        ]

    def scan_gap_limit(self, electrum_client, gap: int = 20) -> int:
        """
        Electrum-style gap limit scan.
        Derives addresses until gap consecutive unused addresses found.
        Returns total number of addresses scanned.
        """
        self._require_unlocked()
        for purpose, addr_type in [(84, "p2wpkh"), (49, "p2sh-p2wpkh"), (44, "p2pkh")]:
            consecutive_empty = 0
            idx = 0
            while consecutive_empty < gap:
                path = self._path(purpose, 0, 0, idx)
                if path not in self._addrs:
                    if self._seed is None:
                        break
                    priv = derive_path(self._seed, path)
                    self._addrs[path] = BitcoinAddress(priv, addr_type, self.network, path)
                addr = self._addrs[path]
                try:
                    history = electrum_client.get_history(addr.electrum_scripthash)
                    if history:
                        consecutive_empty = 0
                    else:
                        consecutive_empty += 1
                except Exception:
                    consecutive_empty += 1
                idx += 1
        return len(self._addrs)

    # ── Keystore: save ────────────────────────────────────────────────────────

    def save(self, filepath: str, password: str):
        self._require_unlocked()
        salt    = secrets.token_bytes(32)
        aes_key = _pbkdf2_key(password, salt)

        secret_blob = json.dumps({
            "mnemonic": self._mnemonic,
            "seed_hex": self._seed.hex() if self._seed else None,
            "network":  self.network,
        }).encode()

        nonce, ciphertext = _aes_gcm_encrypt(aes_key, secret_blob)
        mac = _hmac.new(aes_key, salt + nonce + ciphertext, hashlib.sha256).hexdigest()

        ks = {
            "version":      KEYSTORE_VERSION,
            "nulla_version": NULLA_VERSION,
            "coin":         "BTC",
            "network":      self.network,
            "metadata":     self.metadata,
            "addresses": {
                "default":  self.default_address("p2wpkh").address,
                "segwit":   [a.address for a in self.receiving_addresses("p2wpkh")],
                "legacy":   [a.address for a in self.receiving_addresses("p2pkh")],
            },
            "crypto": {
                "cipher":     "aes-256-gcm",
                "ciphertext": ciphertext.hex(),
                "nonce":      nonce.hex(),
                "mac":        mac,
                "kdf":        "pbkdf2",
                "kdfparams": {
                    "iterations": PBKDF2_ITERATIONS,
                    "hash":       "sha256",
                    "salt":       salt.hex(),
                    "dklen":      32,
                },
            },
        }
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(ks, f, indent=2)
        os.replace(tmp, str(path))

    @classmethod
    def load(cls, filepath: str, password: str) -> "NullaWallet":
        try:
            with open(filepath) as f:
                ks = json.load(f)
        except FileNotFoundError:
            raise KeystoreError(f"Keystore not found: {filepath}")
        except json.JSONDecodeError:
            raise KeystoreError("Corrupted keystore")

        if ks.get("version") != KEYSTORE_VERSION:
            raise KeystoreError(f"Unsupported keystore version {ks.get('version')!r}")

        crypto = ks["crypto"]
        params = crypto["kdfparams"]
        salt    = bytes.fromhex(params["salt"])
        aes_key = _pbkdf2_key(password, salt)
        ct      = bytes.fromhex(crypto["ciphertext"])
        nonce   = bytes.fromhex(crypto["nonce"])

        expected_mac = _hmac.new(aes_key, salt + nonce + ct, hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(expected_mac, crypto["mac"]):
            raise KeystoreError("Wrong password or corrupted keystore")

        try:
            plaintext = _aes_gcm_decrypt(aes_key, nonce, ct)
        except CryptoError:
            raise KeystoreError("Decryption failed")

        secret  = json.loads(plaintext)
        w       = cls()
        w._mnemonic = secret.get("mnemonic")
        w._seed     = bytes.fromhex(secret["seed_hex"]) if secret.get("seed_hex") else None
        w.network   = secret.get("network", ks.get("network", "mainnet"))
        w.metadata  = ks.get("metadata", {})
        w._derive_addresses()
        w._unlocked = True
        return w

    def lock(self):
        for addr in self._addrs.values():
            addr.wipe()
        self._addrs.clear()
        if self._seed:
            self._seed = b"\x00" * len(self._seed)
        self._seed     = None
        self._mnemonic = None
        self._unlocked = False


# ── Keystore crypto ───────────────────────────────────────────────────────────

def _pbkdf2_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32,
        salt=salt, iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    return kdf.derive(password.encode("utf-8"))

def _aes_gcm_encrypt(key: bytes, plaintext: bytes) -> Tuple[bytes, bytes]:
    nonce = secrets.token_bytes(12)
    ct    = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce, ct

def _aes_gcm_decrypt(key: bytes, nonce: bytes, ct: bytes) -> bytes:
    try:
        return AESGCM(key).decrypt(nonce, ct, None)
    except InvalidTag:
        raise CryptoError("GCM tag mismatch")


# ── Utilities ─────────────────────────────────────────────────────────────────

def format_btc(sats: int) -> str:
    """Format satoshis as BTC string."""
    if sats is None:
        return "—"
    btc = abs(sats) / 1e8
    if abs(sats) < 1000:
        return f"{sats} sat"
    return f"{btc:.8f} BTC"

def validate_address(addr: str, network: str = "mainnet") -> bool:
    """Basic Bitcoin address validation."""
    try:
        if addr.startswith(("bc1", "tb1")):
            bech32_decode(addr)
            return True
        raw = base58check_decode(addr)
        return len(raw) == 21
    except Exception:
        return False
