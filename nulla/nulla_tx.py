"""
Nulla — Bitcoin Transaction Builder
Supports P2WPKH (Native SegWit) and P2PKH (Legacy) inputs/outputs.
BIP143 sighash for SegWit inputs.
UTXO coin selection: smallest-first greedy (good for fee efficiency).
"""

import struct
import hashlib
from typing import List, Dict, Optional, Tuple

from nulla_core import BitcoinAddress, hash160, dsha256, sha256

# Dust limit — outputs below this are uneconomical
DUST_LIMIT_P2WPKH = 294   # satoshis
DUST_LIMIT_P2PKH  = 546   # satoshis

# Estimated transaction weight / vbytes
# P2WPKH input: 41 bytes non-witness + 107 witness bytes → ~68 vbytes
# P2PKH input:  148 vbytes
# P2WPKH output: 31 vbytes
# P2PKH output:  34 vbytes
# Tx overhead: 10 vbytes (version, locktime, segwit marker/flag)
VBYTES_OVERHEAD      = 10
VBYTES_P2WPKH_INPUT  = 68
VBYTES_P2PKH_INPUT   = 148
VBYTES_P2WPKH_OUTPUT = 31
VBYTES_P2PKH_OUTPUT  = 34


class TxError(Exception): pass


# ── Encoding helpers ──────────────────────────────────────────────────────────

def _varint(n: int) -> bytes:
    if n < 0xfd:
        return struct.pack("B", n)
    if n <= 0xffff:
        return b"\xfd" + struct.pack("<H", n)
    if n <= 0xffffffff:
        return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)

def _le4(n: int) -> bytes: return struct.pack("<I", n)
def _le8(n: int) -> bytes: return struct.pack("<q", n)  # signed for satoshis

def _push(data: bytes) -> bytes:
    return _varint(len(data)) + data


# ── UTXO selection ────────────────────────────────────────────────────────────

class UTXO:
    def __init__(self, txid: str, vout: int, value: int,
                 address: BitcoinAddress, height: int = 0):
        self.txid    = txid
        self.vout    = vout
        self.value   = value          # satoshis
        self.address = address
        self.height  = height         # 0 = unconfirmed

    @property
    def is_segwit(self) -> bool:
        return self.address.addr_type == "p2wpkh"

    @property
    def outpoint(self) -> bytes:
        return bytes.fromhex(self.txid)[::-1] + struct.pack("<I", self.vout)

    def __repr__(self):
        return f"UTXO({self.txid[:8]}…:{self.vout} = {self.value} sat)"


def select_utxos(utxos: List[UTXO], target: int, fee_rate: int,
                 has_change: bool = True) -> Tuple[List[UTXO], int]:
    """
    Smallest-first UTXO selection.
    Returns (selected_utxos, estimated_fee_sats).
    Raises TxError if insufficient funds.
    """
    # Sort confirmed first, then by value ascending
    sorted_utxos = sorted(utxos, key=lambda u: (u.height == 0, u.value))

    selected = []
    total    = 0
    for utxo in sorted_utxos:
        selected.append(utxo)
        total += utxo.value
        fee    = estimate_fee(selected, 2 if has_change else 1, fee_rate)
        if total >= target + fee:
            return selected, fee

    raise TxError(
        f"Insufficient funds: have {total} sat, need {target + estimate_fee(selected, 2, fee_rate)} sat"
    )


def estimate_fee(inputs: List[UTXO], n_outputs: int, fee_rate: int) -> int:
    """Estimate transaction fee in satoshis."""
    vbytes = VBYTES_OVERHEAD
    for inp in inputs:
        vbytes += VBYTES_P2WPKH_INPUT if inp.is_segwit else VBYTES_P2PKH_INPUT
    # Assume P2WPKH outputs
    vbytes += n_outputs * VBYTES_P2WPKH_OUTPUT
    return max(1, vbytes * fee_rate)


# ── BIP143 sighash (SegWit) ───────────────────────────────────────────────────

def _bip143_sighash(
    inputs: List[UTXO],
    input_index: int,
    outputs: List[Tuple[bytes, int]],    # [(scriptpubkey, sats), ...]
    sighash_type: int = 0x01,
) -> bytes:
    """
    Compute BIP143 sighash for a P2WPKH input.
    https://github.com/bitcoin/bips/blob/master/bip-0143.mediawiki
    """
    utxo = inputs[input_index]

    # 1. nVersion
    version = _le4(2)

    # 2. hashPrevouts
    prevouts = b""
    for inp in inputs:
        prevouts += inp.outpoint
    hash_prevouts = dsha256(prevouts)

    # 3. hashSequence
    sequences = b""
    for _ in inputs:
        sequences += _le4(0xffffffff)
    hash_sequence = dsha256(sequences)

    # 4. outpoint
    outpoint = utxo.outpoint

    # 5. scriptCode for P2WPKH: OP_DUP OP_HASH160 <20> OP_EQUALVERIFY OP_CHECKSIG
    h160 = hash160(utxo.address.pubkey)
    script_code = bytes([0x19, 0x76, 0xa9, 0x14]) + h160 + bytes([0x88, 0xac])

    # 6. value
    value = _le8(utxo.value)

    # 7. nSequence
    sequence = _le4(0xffffffff)

    # 8. hashOutputs
    out_bytes = b""
    for spk, sats in outputs:
        out_bytes += _le8(sats) + _push(spk)
    hash_outputs = dsha256(out_bytes)

    # 9. nLocktime
    locktime = _le4(0)

    # 10. sighash type
    sighash_type_bytes = _le4(sighash_type)

    preimage = (version + hash_prevouts + hash_sequence +
                outpoint + script_code + value + sequence +
                hash_outputs + locktime + sighash_type_bytes)

    return dsha256(preimage)


# ── Legacy sighash (P2PKH) ────────────────────────────────────────────────────

def _legacy_sighash(
    inputs: List[UTXO],
    input_index: int,
    outputs: List[Tuple[bytes, int]],
    sighash_type: int = 0x01,
) -> bytes:
    """Standard SIGHASH_ALL for P2PKH."""
    utxo = inputs[input_index]

    # Serialize inputs (scriptSig empty for all except current)
    inp_bytes = b""
    for i, u in enumerate(inputs):
        spk = u.address.script_pubkey if i == input_index else b""
        inp_bytes += (u.outpoint + _push(spk) + _le4(0xffffffff))

    # Serialize outputs
    out_bytes = b""
    for spk, sats in outputs:
        out_bytes += _le8(sats) + _push(spk)

    raw = (_le4(1) +                       # version
           _varint(len(inputs)) + inp_bytes +
           _varint(len(outputs)) + out_bytes +
           _le4(0) +                       # locktime
           _le4(sighash_type))             # sighash

    return dsha256(raw)


# ── Transaction builder ───────────────────────────────────────────────────────

class TxBuilder:
    """
    Builds and signs a Bitcoin transaction.

    Supports mixed P2WPKH + P2PKH inputs (though pure SegWit preferred).
    Always uses P2WPKH outputs when sending to bech32 addresses.

    Usage:
        builder = TxBuilder(utxos, outputs, change_address, fee_rate)
        raw_hex = builder.build_and_sign()
    """

    def __init__(
        self,
        selected_utxos: List[UTXO],
        outputs: List[Tuple[str, int]],     # [(address_str, sats), ...]
        change_address: BitcoinAddress,
        fee_rate: int = 5,                  # sat/vbyte
        locktime: int = 0,
    ):
        self.utxos          = selected_utxos
        self.raw_outputs    = outputs
        self.change_address = change_address
        self.fee_rate       = fee_rate
        self.locktime       = locktime

        self._outputs: List[Tuple[bytes, int]] = []  # (scriptpubkey, sats)
        self._fee = 0

    def _address_to_scriptpubkey(self, addr: str) -> bytes:
        """Convert any Bitcoin address string to scriptpubkey bytes."""
        from nulla_core import bech32_decode, base58check_decode, \
            MAINNET_P2PKH_VERSION, MAINNET_P2SH_VERSION
        addr = addr.strip()
        if addr.startswith(("bc1", "tb1")):
            _, witver, witprog = bech32_decode(addr)
            if witver == 0 and len(witprog) == 20:
                # P2WPKH
                return bytes([0x00, 0x14]) + witprog
            elif witver == 0 and len(witprog) == 32:
                # P2WSH
                return bytes([0x00, 0x20]) + witprog
            elif witver == 1 and len(witprog) == 32:
                # P2TR (Taproot) — just pass through
                return bytes([0x51, 0x20]) + witprog
            raise TxError(f"Unknown native SegWit version {witver}")
        else:
            raw = base58check_decode(addr)
            ver, h160 = raw[:1], raw[1:]
            if ver == MAINNET_P2PKH_VERSION or ver == b"\x6f":
                # P2PKH
                return bytes([0x76, 0xa9, 0x14]) + h160 + bytes([0x88, 0xac])
            elif ver == MAINNET_P2SH_VERSION or ver == b"\xc4":
                # P2SH
                return bytes([0xa9, 0x14]) + h160 + bytes([0x87])
            raise TxError(f"Unknown address version byte: {ver.hex()}")

    def _build_outputs(self, include_change: bool, change_sats: int):
        self._outputs = []
        for addr, sats in self.raw_outputs:
            self._outputs.append((self._address_to_scriptpubkey(addr), sats))
        if include_change and change_sats > DUST_LIMIT_P2WPKH:
            self._outputs.append((self.change_address.script_pubkey, change_sats))

    def _calc_fee(self, n_outputs: int) -> int:
        return estimate_fee(self.utxos, n_outputs, self.fee_rate)

    def build_and_sign(self) -> str:
        """
        Build, sign, and serialize transaction.
        Returns raw hex string ready for broadcast.
        """
        total_in  = sum(u.value for u in self.utxos)
        total_out = sum(sats for _, sats in self.raw_outputs)

        if total_out <= 0:
            raise TxError("Output amount must be positive")

        # Calculate fee with change output
        fee_with_change    = self._calc_fee(len(self.raw_outputs) + 1)
        fee_without_change = self._calc_fee(len(self.raw_outputs))
        change_sats        = total_in - total_out - fee_with_change

        if change_sats < 0:
            raise TxError(f"Insufficient funds (need {total_out + fee_with_change} sat, have {total_in} sat)")

        include_change = change_sats > DUST_LIMIT_P2WPKH
        self._fee = fee_with_change if include_change else fee_without_change

        self._build_outputs(include_change, change_sats)

        # Sign all inputs
        has_segwit = any(u.is_segwit for u in self.utxos)
        sigs: List[Tuple[bytes, bytes]] = []  # (sig, pubkey) per input

        for i, utxo in enumerate(self.utxos):
            if utxo.is_segwit:
                sighash = _bip143_sighash(self.utxos, i, self._outputs)
            else:
                sighash = _legacy_sighash(self.utxos, i, self._outputs)

            raw_sig = utxo.address.sign_hash(sighash)
            # Append SIGHASH_ALL byte
            der_sig = raw_sig + bytes([0x01])
            sigs.append((der_sig, utxo.address.pubkey))

        # Serialize
        raw = self._serialize(sigs, has_segwit)
        return raw.hex()

    def _serialize(self, sigs: List[Tuple[bytes, bytes]], segwit: bool) -> bytes:
        version  = _le4(2)
        locktime = _le4(self.locktime)

        # Inputs (scriptSig depends on type)
        inp_bytes = _varint(len(self.utxos))
        for i, utxo in enumerate(self.utxos):
            sig, pub = sigs[i]
            if utxo.is_segwit:
                script_sig = b""    # SegWit: scriptSig is empty
            else:
                # Legacy: scriptSig = <sig> <pubkey>
                script_sig = _push(sig) + _push(pub)
            inp_bytes += (utxo.outpoint + _push(script_sig) + _le4(0xffffffff))

        # Outputs
        out_bytes = _varint(len(self._outputs))
        for spk, sats in self._outputs:
            out_bytes += _le8(sats) + _push(spk)

        if segwit:
            # Witness data per input
            witness = b""
            for i, utxo in enumerate(self.utxos):
                sig, pub = sigs[i]
                if utxo.is_segwit:
                    # 2 stack items: sig + pubkey
                    witness += _varint(2) + _push(sig) + _push(pub)
                else:
                    witness += _varint(0)  # No witness for legacy inputs

            return (version +
                    b"\x00\x01" +  # Segwit marker + flag
                    inp_bytes +
                    out_bytes +
                    witness +
                    locktime)
        else:
            return version + inp_bytes + out_bytes + locktime

    @property
    def fee(self) -> int:
        return self._fee


# ── Helper: build a full send transaction ────────────────────────────────────

def build_send_tx(
    all_utxos: List[UTXO],
    to_address: str,
    amount_sats: int,
    change_address: BitcoinAddress,
    fee_rate: int = 5,
) -> Tuple[str, int, int]:
    """
    High-level transaction builder.
    Returns (raw_tx_hex, fee_sats, change_sats).
    """
    selected, fee = select_utxos(all_utxos, amount_sats, fee_rate)
    builder = TxBuilder(
        selected_utxos=selected,
        outputs=[(to_address, amount_sats)],
        change_address=change_address,
        fee_rate=fee_rate,
    )
    raw_hex = builder.build_and_sign()
    total_in  = sum(u.value for u in selected)
    change    = total_in - amount_sats - builder.fee
    return raw_hex, builder.fee, max(0, change)
