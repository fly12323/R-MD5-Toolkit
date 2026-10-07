"""Independent MD5 research primitives, specified by RFC 1321.

This module is NOT a collision generator. Differential-path search remains
unimplemented. Known collision samples belong only in tests.
"""
import math
import struct

MASK = 0xffffffff
IV = (0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476)
SHIFTS = (7, 12, 17, 22) * 4 + (5, 9, 14, 20) * 4 + (4, 11, 16, 23) * 4 + (6, 10, 15, 21) * 4
CONSTANTS = tuple(int(abs(math.sin(i + 1)) * 2**32) for i in range(64))


def rotate_left(word, count):
    word &= MASK
    return ((word << count) | (word >> (32 - count))) & MASK


def rotate_right(word, count):
    word &= MASK
    return ((word >> count) | (word << (32 - count))) & MASK


def round_function(step, b, c, d):
    if step < 16:
        return (b & c) | (~b & d)
    if step < 32:
        return (b & d) | (c & ~d)
    if step < 48:
        return b ^ c ^ d
    return c ^ (b | ~d)


def word_index(step):
    if not 0 <= step < 64:
        raise ValueError('step must be in 0..63')
    if step < 16:
        return step
    if step < 32:
        return (5 * step + 1) % 16
    if step < 48:
        return (3 * step + 5) % 16
    return (7 * step) % 16


def next_q(step, a, b, c, d, message_word):
    value = (a + round_function(step, b, c, d) + CONSTANTS[step] + message_word) & MASK
    return (b + rotate_left(value, SHIFTS[step])) & MASK


def recover_word(step, a, b, c, d, target_q):
    """Invert a single MD5 step for the message word, modulo 2**32."""
    word_index(step)
    return (rotate_right((target_q - b) & MASK, SHIFTS[step])
            - a - round_function(step, b, c, d) - CONSTANTS[step]) & MASK


def compress(block, state=IV, with_trace=False):
    if len(block) != 64:
        raise ValueError('compression requires exactly 64 bytes')
    if len(state) != 4 or any(not isinstance(x, int) or not 0 <= x <= MASK for x in state):
        raise ValueError('state must contain four uint32 words')
    words = struct.unpack('<16I', block)
    a, b, c, d = state
    # q[0..3] = Q[-3], Q[-2], Q[-1], Q[0] = A, D, C, B.
    q = [a, d, c, b]
    for step in range(64):
        q.append(next_q(step, q[step], q[step + 3], q[step + 2], q[step + 1], words[word_index(step)]))
    working = (q[64], q[67], q[66], q[65])
    result = tuple((x + y) & MASK for x, y in zip(state, working))
    return (result, tuple(q)) if with_trace else result


def padding(length):
    if not isinstance(length, int) or length < 0:
        raise ValueError('length must be a nonnegative byte count')
    return b'\x80' + b'\0' * ((55 - length) % 64) + struct.pack('<Q', (length * 8) & 0xffffffffffffffff)


def hexdigest(data):
    padded = data + padding(len(data))
    state = IV
    for offset in range(0, len(padded), 64):
        state = compress(padded[offset:offset + 64], state)
    return struct.pack('<4I', *state).hex()


def modify_first_round(block, constraints, state=IV):
    """Enforce Q1..Q16 bit masks by inverting first-round message words.

    constraints maps step 1..16 to (mask, target_bits). This establishes
    first-round conditions only; it does NOT preserve later-round conditions
    or guarantee a differential path or a collision.
    """
    if len(block) != 64:
        raise ValueError('message modification requires a 64-byte block')
    for step, (mask, bits) in constraints.items():
        if not isinstance(step, int) or not 1 <= step <= 16:
            raise ValueError('first-round constraints require step 1..16')
        if not 0 <= mask <= MASK or not 0 <= bits <= MASK or bits & ~mask:
            raise ValueError('invalid constraint mask/target bits')
    words = list(struct.unpack('<16I', block))
    a, b, c, d = state
    q = [a, d, c, b]
    for step in range(16):
        target = next_q(step, q[step], q[step + 3], q[step + 2], q[step + 1], words[step])
        if step + 1 in constraints:
            mask, bits = constraints[step + 1]
            target = (target & ~mask) | bits
            words[step] = recover_word(step, q[step], q[step + 3], q[step + 2], q[step + 1], target)
        q.append(target)
    return struct.pack('<16I', *words)


def differential_trace(first, second):
    """Trace paired full blocks, including chaining-state feed-forward."""
    if len(first) != len(second) or len(first) % 64:
        raise ValueError('paired messages must have equal lengths divisible by 64')
    left, right = IV, IV
    blocks = []
    for offset in range(0, len(first), 64):
        a, b = first[offset:offset + 64], second[offset:offset + 64]
        input_delta = [(y - x) & MASK for x, y in zip(left, right)]
        left, qa = compress(a, left, True)
        right, qb = compress(b, right, True)
        blocks.append({'block': offset // 64, 'input_state_delta': input_delta,
                       'message_word_delta': [(y - x) & MASK for x, y in zip(struct.unpack('<16I', a), struct.unpack('<16I', b))],
                       'q_delta': [(y - x) & MASK for x, y in zip(qa[4:], qb[4:])],
                       'q_xor': [x ^ y for x, y in zip(qa[4:], qb[4:])],
                       'output_state_delta': [(y - x) & MASK for x, y in zip(left, right)]})
    return {'blocks': blocks, 'same_chaining_state': left == right,
            'md5_left': hexdigest(first), 'md5_right': hexdigest(second),
            'collision': first != second and hexdigest(first) == hexdigest(second)}
