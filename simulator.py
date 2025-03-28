def to_binary32(val):
    """Convert an integer to a 32-bit binary string with a 0b prefix."""
    return "0b" + format(val & 0xFFFFFFFF, '032b')

def sign_extend(value, bits):
    """Sign-extend a value of given bit-width."""
    if value & (1 << (bits - 1)):
        value -= (1 << bits)
    return value

def decode_I_type(inst):
    rd  = (inst >> 7) & 0x1F
    funct3 = (inst >> 12) & 0x7
    rs1 = (inst >> 15) & 0x1F
    imm = sign_extend((inst >> 20) & 0xFFF, 12)
    return rd, funct3, rs1, imm

def decode_R_type(inst):
    rd  = (inst >> 7) & 0x1F
    funct3 = (inst >> 12) & 0x7
    rs1 = (inst >> 15) & 0x1F
    rs2 = (inst >> 20) & 0x1F
    funct7 = (inst >> 25) & 0x7F
    return rd, funct3, rs1, rs2, funct7

def decode_B_type(inst):
    funct3 = (inst >> 12) & 0x7
    rs1 = (inst >> 15) & 0x1F
    rs2 = (inst >> 20) & 0x1F
    imm = (((inst >> 31) & 0x1) << 12) | (((inst >> 7) & 0x1) << 11) | \
          (((inst >> 25) & 0x3F) << 5) | (((inst >> 8) & 0xF) << 1)
    imm = sign_extend(imm, 13)
    return funct3, rs1, rs2, imm
def decode_J_type(inst):
    rd = (inst >> 7) & 0x1F
    imm = (((inst >> 31) & 0x1) << 20) | (((inst >> 21) & 0x3FF) << 1) | \
          (((inst >> 20) & 0x1) << 11) | (((inst >> 12) & 0xFF) << 12)
    imm = sign_extend(imm, 21)
    return rd, imm


def execute_instruction(inst, registers, memory):
    """Decode and execute one instruction."""
    opcode = inst & 0x7F
    pc_increment = 4  # default increment
    halt = False

    if opcode == 0x33:  # R-type instructions
        rd, funct3, rs1, rs2, funct7 = decode_R_type(inst)
        if funct3 == 0 and funct7 == 0:  # add
            registers[rd] = (registers[rs1] + registers[rs2]) & 0xFFFFFFFF
        elif funct3 == 0 and funct7 == 0x20:  # sub
            registers[rd] = (registers[rs1] - registers[rs2]) & 0xFFFFFFFF
        elif funct3 == 2 and funct7 == 0:  # slt
            rs1_val = registers[rs1] if registers[rs1] < 0x80000000 else registers[rs1] - 0x100000000
            rs2_val = registers[rs2] if registers[rs2] < 0x80000000 else registers[rs2] - 0x100000000
            registers[rd] = 1 if rs1_val < rs2_val else 0
        elif funct3 == 5 and funct7 == 0:  # srl
            shamt = registers[rs2] & 0x1F
            registers[rd] = (registers[rs1] & 0xFFFFFFFF) >> shamt
        elif funct3 == 6 and funct7 == 0:  # or
            registers[rd] = registers[rs1] | registers[rs2]
        elif funct3 == 7 and funct7 == 0:  # and
            registers[rd] = registers[rs1] & registers[rs2]
        else:
            print("Unsupported R-type instruction encountered.")
    elif opcode == 0x63:  # B-type instructions
        funct3, rs1, rs2, imm = decode_B_type(inst)
        if funct3 == 0:  # beq
            if registers[rs1] == registers[rs2]:
                if imm == 0:
                    halt = True
                else:
                    pc_increment = imm
        elif funct3 == 1:  # bne
            if registers[rs1] != registers[rs2]:
                if imm == 0:
                    halt = True
                else:
                    pc_increment = imm
        elif funct3 == 4:  # blt
            rs1_val = registers[rs1] if registers[rs1] < 0x80000000 else registers[rs1] - 0x100000000
            rs2_val = registers[rs2] if registers[rs2] < 0x80000000 else registers[rs2] - 0x100000000
            if rs1_val < rs2_val:
                if imm == 0:
                    halt = True
                else:
                    pc_increment = imm
        else:
            print("Unsupported B-type instruction encountered.")
    elif opcode == 0x13 or opcode == 0x67 or opcode == 0x3:
        # I-type instructions
        rd, funct3, rs1, imm = decode_I_type(inst)
        if funct3 == 0 and opcode == 0x13:  # addi
            registers[rd] = (registers[rs1] + imm) & 0xFFFFFFFF
        elif funct3 == 0 and opcode == 0x67:  # jalr
            temp = registers[rs1] + imm
            registers[rd] = pc_increment
            pc_increment = temp & 0xFFFFFFFE
        elif funct3 == 2 and opcode == 0x3:  # lw
            addr = (registers[rs1] + imm) & 0xFFFFFFFF
            registers[rd] = memory.get(addr, 0)
        else:
            print("Unsupported I-type instruction encountered.")
    elif opcode == 0x6F:  # J-type instructions (JAL)
        rd, imm = decode_J_type(inst)
        if rd != 0:  # If rd is not x0, store return address
            registers[rd] = (pc + 4) & 0xFFFFFFFF
        pc_increment = imm  # Jump to the new address
    else:
        print("Unsupported opcode encountered.")

    registers[0] = 0  # x0 is always zero
    return pc_increment, halt

def format_trace_line(pc, registers):
    reg_str = " ".join(to_binary32(r) for r in registers)
    return f"{to_binary32(pc)} {reg_str}"

def format_memory_dump(memory):
    lines = []
    for addr in sorted(memory.keys()):
        lines.append(f"0x{addr:08X}:{to_binary32(memory[addr])}")
    return lines

print("Enter the input machine code file (e.g., simple_1.txt):")
input_file = input().strip()
print("Enter the output trace file (e.g., trace.txt):")
output_file = input().strip()

with open(input_file, 'r') as fin:
    instructions = [line.strip() for line in fin if line.strip()]

# First instruction at PC=4, then 8, 12, ...
instr_mem = {4 * (i + 1): instructions[i] for i in range(len(instructions))}
registers = [0] * 32
registers[2] = 380  # Initialize stack pointer (x2) to 380.
pc = 4

# Data memory: 32 locations from 0x00010000 to 0x0001007C.
data_mem = {addr: 0 for addr in range(0x00010000, 0x00010080, 4)}

trace_lines = []

# Simulation loop
while pc in instr_mem:
    inst_bin = instr_mem[pc]
    inst_int = int(inst_bin, 2)
    pc_inc, halt = execute_instruction(inst_int, registers, data_mem)
    if halt:
        break
    trace_lines.append(format_trace_line(pc, registers))
    pc += pc_inc
pc -= pc_inc
trace_lines.append(format_trace_line(pc, registers))

# Append memory dump immediately
trace_lines.extend(format_memory_dump(data_mem))

with open(output_file, 'w') as fout:
    for line in trace_lines:
        fout.write(line + "\n")
        
print("Simulation complete. Trace written to", output_file)
