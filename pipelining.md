# Preface

I decide to submit this note as an "issue" rather than in other ways so one ...
Since I do not know Verilog nor SMG used in KCP53000 that well, so I decide to instead
write everything in a descriptive way so one with a technical knowledge can understand and implement
this.

# The register writeout pipelining algorithm

The _register writeout pipelining_ is all about having the final result being written out
to the destination register while at the same time an instruction is being fetched. This
simple pipelining makes the last cycle of the current instruction overlap with the first
cycle of the next instruction, thus saving a cycle on most instructions. This should work
on the following groups of instructions: LOAD; all instructions that uses ALU, like ADD,
SLL, etc.; JAL/JALR; AUIPC; LUI; and instructions that manipulates CSR registers.

Now, in the current implementation, the destination register is obtained directly from the
instruction register ('ir[11:7]`), which must stay valid for the entire execution of the
instruction. Naturally this will be a problem if one want to implement this pipelining
method. Since the pipelining is really all about maintaining several states, one for each
instruction being processed, so it is necessary to separate out the dependencies.
Fortunately, since by the final cycle of the execution of the current instruction, much
action obtained from the decoding of the current has been carried out, so we only need to
extract small remaining activity and bundle it off under a separate "state".

With that in mind, here's how to do it:
First, define a register cache, call it `rdhold`. Declare this in polaris.v like this:
```
    wire  [4:0] rdhold;
```
Then insert a line in the file `seq.smg` like this:
```
 [on [~rst xt0]   rdhold_rd]
```
This line says that on the cycle right after the instruction is fetched, copy the rd
field into `rdhold`. I elect to do it for _any_ instruction since I expect the logic
synthesis to be minimal and simple. It also lets us separate the dependency of rd from
the instruction register. To round out that implementation, insert a line in `polaris.v`:
```
    assign rdhold = ir[11:7];
```

Now, since various signals that forms the state are directly dependent on the instruction
field, we need to create a separate state divorced from that dependency, and have each
next-to-last cycle of the instruction hand it off to that state.

```
old version:
 [on [~rst xt0 isOpI]           xt1_o ra_ir1]
 [on [~rst xt1 isOpI]           xt2_o alua_rdat alub_imm12i]
 [on [~rst xt2 isOpI]           ra_ird rdat_alu rwe_o useAlu ft0_o]

new version:
 [on [~rst xt0 isOpI]           xt1_o ra_ir1]
 [on [~rst xt1 isOpI]           ft0_o alua_rdat alub_imm12i]
 [on [~rst ft0 isOpI]           ra_ird rdat_alu rwe_o useAlu]

old version:
 [on [~rst xt0 isOpR]           xt1_o ra_ir1]
 [on [~rst xt1 isOpR]           xt2_o alua_rdat ra_ir2]
 [on [~rst xt2 isOpR]           xt3_o alub_rdat]
 [on [~rst xt3 isOpR]           ra_ird rdat_alu rwe_o useAlu2 ft0_o]

new version:
 [on [~rst xt0 isOpR]           xt1_o ra_ir1]
 [on [~rst xt1 isOpR]           xt2_o alua_rdat ra_ir2]
 [on [~rst xt2 isOpR]           ft0_o alub_rdat]
 [on [~rst ft0 isOpR]           ra_ird rdat_alu rwe_o useAlu2]
```
