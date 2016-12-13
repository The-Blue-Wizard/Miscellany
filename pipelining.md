# Preface

I decide to submit this note as an "essay" rather than in other ways so I can post it
for the readers...perhaps as a guest article on official Kestrel website.

Since I do not know Verilog nor SMG used in KCP53000 that well, so I decide to instead
write everything in a descriptive way so one with a technical knowledge can understand
and implement this.

# The register writeout pipelining algorithm

The _register writeout pipelining_ is all about having the final result being written out
to the destination register while at the same time an instruction is being fetched. This
simple pipelining makes the last cycle of the current instruction overlap with the first
cycle of the next instruction, thus saving a cycle on most instructions. This should work
on the following groups of instructions: all instructions that uses ALU, like ADD,
SLL, etc.; AUIPC and LUI. Although I _may_ be wrong, but I don't think it would work for
LOAD (since I think the data bus must be kept active on the last cycle for data to go
into the register file, and that conflicts with the instruction fetching), JAL/JALR (since
it looks like the register writeout happens in the first step, which can't be applied),
and CSR instructions (same reason).

Now, in the current implementation, the destination register is obtained directly from the
instruction register (`ir[11:7]`), which must stay valid for the entire execution of the
instruction. Naturally this will be a problem if one want to implement this pipelining
method. Since the pipelining is really all about maintaining several states, one for each
instruction being processed, so it is necessary to separate out the dependencies.
Fortunately, since by the final cycle of the execution of the current instruction, much
action obtained from the decoding of the current has been carried out, so we only need to
extract small remaining activity and bundle it off under a separate "state".

I also observe that I need to make a copy of fn3 field since that will be used in the
last step of the ALU instruction.

I also must note that the interrupt must allow the final cycle to complete, no matter what.

With those things in mind, here's how I would do it:

First, define a register cache, call it `rdhold`. Also define a variable called `fn3`.
Declare this in `polaris.v` like this:
```
    wire  [4:0] rdhold;
    wire  [2:0] fn3;
```
Then insert a line in the file `seq.smg` like this:
```
 [on [~rst xt0]   rdhold_rd fn3_ir]
```
This line says that on the cycle right after the instruction is fetched, copy the rd
field into `rdhold` and the fn3 field (I'm deliberately ignoring the instruction formats
here) into fn3. I elect to do it for _any_ instruction since I expect the logic
synthesis to be minimal and simple. It also lets us separate the dependency of rd from
the instruction register. To round out that implementation, insert two line in `polaris.v`:
```
    assign rdhold = ir[11:7];
    assign fn3    = ir[14:12];
```

Then I would recode:
```
 [on [["ir[14:12]" 3'b000]]     fn3_is_000]
 etc.
```
to
```
 [on [[fn3 3'b000]]     fn3_is_000]
 etc.
```
in `seq.smg` file.

Now, since various signals that forms the state are directly dependent on the instruction
field, we need to create a separate state divorced from that dependency, and have each
next-to-last cycle of the instruction hand it off to that state.

So I make `isOpI`, `isOpR` and `isLuiAuipc` flags that is maintained separately
from the `ir[...]`. So, `isOpI_o`, `isOpR_o` and `isLuiAuipc_o` are also needed,
to meet this new requirement. These are also added to `polaris.v` as needed.

Now, modify the following sections in `seq.smg` file like this:

```
old version of OPIMM:
 [on [~rst xt0 isOpI]           xt1_o ra_ir1]
 [on [~rst xt1 isOpI]           xt2_o alua_rdat alub_imm12i]
 [on [~rst xt2 isOpI]           ra_ird rdat_alu rwe_o useAlu ft0_o]

new version of OPIMM:
 [on [~rst xt0 ["ir[6:4]" "3'b001"] ["ir[2:0]" "3'b011"]]   isOpI_o xt1_o ra_ir1]
 [on [~rst xt1 isOpI]           ft0_o alua_rdat alub_imm12i isOpI_o]
 [on [~rst ft0 isOpI]           ra_ird rdat_alu rwe_o useAlu]

old version of OPR:
 [on [~rst xt0 isOpR]           xt1_o ra_ir1]
 [on [~rst xt1 isOpR]           xt2_o alua_rdat ra_ir2]
 [on [~rst xt2 isOpR]           xt3_o alub_rdat]
 [on [~rst xt3 isOpR]           ra_ird rdat_alu rwe_o useAlu2 ft0_o]

new version of OPR:
 [on [~rst xt0 isOpR]           xt1_o ra_ir1]
 [on [~rst xt1 isOpR]           xt2_o alua_rdat ra_ir2]
 [on [~rst xt2 isOpR]           ft0_o alub_rdat isOpR_last_o]
 [on [~rst ft0 isOpR_last]      ra_ird rdat_alu rwe_o useAlu2]

old version of LUI/AUIPC:
 [on ["~ir[6]" ["ir[4:0]" "5'b10111"]]  isLuiAuipc]
 [on [~rst xt0 isLuiAuipc]              xt1_o alub_imm20u]
 [on [~rst xt0 isLuiAuipc "ir[5]"]      alua_0]
 [on [~rst xt0 isLuiAuipc "~ir[5]"]     alua_ia]
 [on [~rst xt1 isLuiAuipc]              ra_ird rdat_alu rwe_o sum_en ft0_o]

new version of LUI/AUIPC:
 [on [~rst xt0 "~ir[6]" "ir[5]"  ["ir[4:0]" "5'b10111"]]  ft0_o alua_0  alub_imm20u isLuiAuipc_o]
 [on [~rst xt0 "~ir[6]" "~[ir5]" ["ir[4:0]" "5'b10111"]]  ft0_o alua_ia alub_imm20u isLuiAuipc_o]
 [on [~rst ft0 isLuiAuipc]      ra_ird rdat_alu rwe_o sum_en ft0_o]
```

It is completely possible that I am overlooking some other stuff, since there
are many little stuff I have little or no real understanding of, so I shall
leave it to someone else to review.

# Conclusion

It is my hope that these simple modifications would make Polaris go a bit
faster, maybe enough to close an outstanding issue regarding Polaris being
"too slow to be useful". I thought I might hit 25% gain in throughput, but
now with LOAD and JAL/JALR out of picture, I would settle for 20% gain.
That would mean we would be seeing 7 MIPS instead of 6 MIPS, not 8 MIPS as
I hope. But maybe therein lies some hidden opportunities for better
optimization. We shall see! (smile)

I also learned something from this exercise. Sometimes with the right
insight it can become simpler. It also can get more complicated. I find
that an interesting lesson.
