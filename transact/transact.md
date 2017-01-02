# A new "idea":  (lightweight) transactional execution (or transactional processing)

Here's an example illustrating this new "idea" (pseudocode):

~~~~
   transact {
      construct URL
      error invalid URL: ....

      open( ... )
      error "can't open: ..." 
      cleanup: close( ... )
      complete with no error: ...

      read( ... )
      error EOF: close and continue on

      etc.
   }
~~~~

The idea is that instead of nested try/catch stuff, we can wrap it into `transact {}`
statement and have localized error (our "catch" statements) deal with them individually,
then "break" out of transact body naturally (more or less like switch statement, kinda).
Thus in this particular example, if an invalid URL construction happens, it is dealt
with, and the "open" and subsequent statements don't get executed at all! And as a
bonus, one would not have to use `goto` statement, or similar hacks. Nice, IMHO!

Future addition:  `retry` statement would let you retry the transact, much like a
C's `continue` statement would in a loop. But `retry` would be more intelligent...it
would go back to the last "good run" point inside the transact body.

## Problem addressed

This new construct should alleviate the need for messy try/catch/exception
constructs, lessen the dependence on `atexit()` service, promote the code locality,
and increase readability and maintainability.

## C version

I initially thought to merely implement a syntactic structure quite similar to that
shown in the example. But, as I thought more about it, I realized it would be better
to expand the meaning of the block instead. In other words, `transact { }` would get
absorbed into the surrounding block. An advantage of this approach is that I get
transactional coding for free at all level (inside a function body only, of course).
Also, C does not have the exception handling facility (C++'s try....catch thing), so
I had to reduce the semantic of transactional execution a bit.

So, after having some more thought and some designing, here is the new syntax extension
for C (note it may be grammatically ambiguous):

```yacc
statement:
    compound-statement
    jump-statement
    check-statement
    /* etc. */

check-statement:
    "__check" expression ";"

jump-statement:
    "goto" identifier ";"
    "goto" transaction-start ";"
    "continue" ";"
    /* etc. */

transaction-start:
    "__error"
    "__finally"
    "__success"
    "__failure"

compound-statement:
    "{" block-section-list.opt "}"

block-section-list:
    block-section
    block-section-list block-section

block-section:
    block-item-list
    block-section transaction block-item-list

block-item-list:
    block-item
    block-item-list block-item

block-item:
    declaration
    statement

transaction:
    error-stmt.opt  success-stmt.opt  failure-stmt.opt  finally-stmt.opt

error-stmt:
    "__error" statement

finally-stmt:
    "__finally" statement

success-stmt:
    "__success" statement

failure-stmt:
    "__failure" statement
```

As you can see, four new transaction phrases are introduced, along with an expanded
"goto" construct, and the general rules of usage should be fairly clear.

As a further constraint, the "main statement" (which is either a 'regular'
statement or a main block, but the subblock may be excluded) inside `success-stmt`
and `failure-stmt` may not contain `goto __error`, and the `failure-stmt` may have
only `goto __failure`, as all forbidden choices are semantically meaningless.

## Behavior

First, some definitions shall be made in order to keep the exposition clear.

For the purpose of discussion, the block shall be divided into "sections", where
a section is defined as a particular group of consecutive `block-items` that has a
series of declarations and statements, and ends with a transaction, if present.
Note that the absence of a transaction in a block section can only occur as the
last such section in a block.

A chain is a series of certain statement parts found in the transactions in a block.
It is typically built up so that an execution of the chain runs in a "backwards"
fashion, which will be explained later.  There are two such chains, one is called
a success chain, and the other is called an error/failure chain.

Now, the behavior of these statements follows:

The `__check` statement is completely equivalent to the C code:

```C
    if ( !(expression) ) goto __error;
```

Thus the idea is to check to make sure the conditions remain valid. For example,
`__check( ptr != NULL )` checks to make sure the pointer variable `ptr` is not `NULL`.
This `__check` statement is provided as a natural transact semantic sugar construct.
Note that it is different than the `assert()` macro, which is used more for diagnostic
purpose rather than for 'defensive' programming.

Invoking `goto __error` in the the `statement` portion of the block section shall
initiate an error/failure chain.

If the `goto __error` statement is never executed by the time a transaction is
reached, then it shall skip over the remaining portion of that transaction and
continue on to the next block section.

Executing `goto __success` in the the `statement` portion of the block section
shall initiate a success chain.

The success chain runs as follows:
  * Starting with a current block section, go through a series of previous
    transactions, executing a `__success` statement (if present) and then
    executing `__finally` statement (if present) in turn, until one of the
    following happens:</br>
        1. a `goto __success` or a `goto __finally` statement is reached,</br>
        2. a `goto __failure` statement is reached, or</br>
        3. there are no more previous transactions to process.</br>
  * For the first case, it simply exits the `__success` block and resumes the
    chain traversal described above.
  * For the second case, it shall initiate the error/failure chain by going
    straight to the first `__failure` statement (the `__error` statement is
    *NEVER* invoked here!).
  * The third case simply causes it to exit the current block, and if that
    block is nested inside another block, the success chain proceeds in that
    outer block, all the way up to the outermost block, and in that case, it
    simply goes to the end of the block, as if there is an invisible label
    tagged to the end of the outermost block with an invisible goto statement
    pointing to that label.

The error/failure chain runs as follows:
  * Starting with a current block section, go through a series of previous
    transactions, executing a `__failure` statement (if present) and then
    executing `__finally` statement (if present) in turn, until one of the
    following happens:</br>
        1. a `goto __failure` or a `goto __finally` statement is reached, or</br>
        2. there are no more previous transactions to process.</br>
  * For the first case, it simply exits the `__failure` block and resume the
    chain traversal described above.
  * The second case simply causes it to exit the current block, and if that
    block is nested inside another block, the success chain proceeds in that
    outer block, all the way up to the outermost block, and in that case, it
    simply goes to the end of the block, as if there is an invisible label
    tagged to the end of the outermost block with an invisible goto statement
    pointing to that label.

Note that the execution of transaction chain never goes outside the function
itself. So there is no stack traversal at all, which is one point that makes
it a lightweight flavor to structured coding.

## Transact Coding Logic

Rule #1:  `goto __error` without corresponding `__error` transact is illegal.

Rule #2:  `__error` transact without corresponding `goto __error` is illegal.

Rule #1 and #2 can be checked in `section_coda()` by this:

~~~~
    (gotostmtseen ^ transactseen) & ERROR:  0 means OK; not 0 means illegal
~~~~

Rule #3:  `goto __success/__failure/__finally` without corresponding
          `__success/__failure/__finally` transact is OK! In these cases,
          all these gotos jump to the closest `__success/__failure/__finally`
          transact in previous section.  (actually it is more nuanced
          than that, but you get the idea...)

Rule #4:  `__success/__failure/__finally` transact without corresponding
          `goto __success/__failure/__finally` is OK!

Rule #5:  There is no default `__error` transact (hence the reason for rule
          #1 and #2), and the default `__success` transact consists of just
          `goto __finally`, and the default `__failure` transact has:
```C
              _tfailure = 1;
              goto __finally;
```
          And the default `__finally` transact has (pseudocode):
```C
              if (_tfailure) goto __'prev'failure;
              else           goto __'prev'success;
```

Rule #6:  All transacts, whether explicit or default, start with a
          label `_tNNSSx:`, where `x` is one of four possible letters
          'e', 's', 'f', and 'c'.

Rule #7:  The "final" labels are placed at the end...

Rule #8:  Subblocks can contain only `__error` transacts, due to logistical
          constraints. In other words, putting `__success` and other
          transacts in those subblocks doesn't make sense. For instance,
          what if the routine reaches the "success" stage, after it has
          gone through an if/else statement, with each block containing a
          `__success` transact?  How would it pick out which `__success`
          transacts in the subblocks to execute? Similar reasoning goes
          for `__failure` and `__finally` transacts. Of course this makes
          subblocks somewhat awkward to deal with from a certain
          programming standpoint.

(Idea:  The `__transact` could be used temporarily to just trigger a series
        of default constructions for quick development)

# The Algorithm

The algorithm for transforming a block containing these stuff:

1. Right after seeing an opening block `{` in the function definition, add
   `int __tfailure = 0;` after it. Note that this variable is function wide,
   which is critical to the proper execution of chain traversal.
2. Set nesting level to 0. Initialize a "history" stack with its first
   entry being zero, which indicates default label for end of the outermost
   block.
3. Set block section counter to 1. The zero for the block section counter
   is reserved to mean the default label for the end of that block. Clear
   the gototracker (see (4)).
4. Scan through the code, finding `goto __xxx;`  forms, and convert it to
   `goto __tNNSSx;` where `NN` is the Nth nested block being processed, `SS` is
   the current block section counter, and `x` is one of the four letters "e",
   "s", "f" and "c", where each corresponds to `__error`, `__success`,
   `__failure` and `__finally`, respectively (note: "c" == cleanup).
   Also, make note of such encounter (this can be done by OR'ing the
   gototracker variable by an appropriate bitflag).
5. If an opening block token `{` is encountered anywhere before a
   transaction is encountered, increment the nesting level by 1, save the
   block section counter onto a "history" stack, and go to (3).
6. If a closing block token `}` is encountered anywhere before a
   transaction is encountered, decrement the nesting level by 1, restore the
   block section counter from a "history" stack, and go to (4).
7. Upon encountering one of the four transaction tokens for the first time,
   namely `__error`, `__success`, `__failure` and `__finally`, output a
   `goto __tNN(SS+1);` where `SS+_1` obviously refers to the next section, and
   clear the transaction token bitvector, and go to (8).
8. At the point of the transaction token (which is one of `__error`,
   `__success`, `__failure` and `__finally`), output the label `__tNNSSx:`
   where `NN` and `SS` are Nth nested block and current block section counter,
   respectively. Set transaction token bitvector to one that corresponds
   to the current transaction token. If it is already set, print an
   error message "transaction point multiply defined" and continue.
   1. Set or clear the brace flag based on whether the next token is a
      `{`, output a `{`, and if the transaction token is a `__failure`
      token, output a `__tfailure = 1;` as well.
   2. ...
   3. If the brace flag is set and the next token isn't a `}`, go to (8ii).
   4. For an `__error` statement, output a `goto __tNNSSf;`, and for both
      `__success` and `__failure` statements, output a `goto __tNNSSx;`,
      and lastly, for `__finally` statement, output a `goto __t?????;`.
      Then output a `}`.
   5. If the next token is not a transaction token, then output the
      label `__tNNSSx:  goto __t?????` if `__finally` statement never
      have appeared, then output another label `__tNN(SS+1):`.

## Implementation

I initially prototyped up the transaction logic and algorithm using Python,
mainly to figure out the algorithm, debug it and for demonstration purpose.

The initial implementation for C is admittedly crude. I grabbed cflow code
and munge it quickly, based on the algorithm developed in the Python version.

## Case Study

I selected three C programs, namely ...

## Lessons Learned

I find that developing unit tests to be helpful, but the effort involved
seems to require some forethought, and I haven't bothered to learn the
Python's UnitTest facility, in part because of the steep learning curve
involved, and because I discovered that it is easier to encode types of
testing straight inside the test files themselves.

## Possible Future Improvements

Several improvements could be made, and here are a few ideas:

1. Permit the use of `__success/__failure/__finally` transacts in subblocks.
   Of course it is a rather hard problem.
2. Introduce `__commit` statement.  The behavior of `__commit` is to execute
   all `__success/__finally` transacts "issued" to this point, then resume
   the exection after the `__commit`. Interesting, and rather hard.
3. `goto __next`...
4. Reset the `_tfailure` flag so it can resume (desirable in some context).
5. Any other ideas?

--- John "The Blue Wizard" Rogers
