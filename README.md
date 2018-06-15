# bgu-aitesting-testoptimizer

Project for finding optimal sub set of test that will give the max bugs using Information gain.

Each test have component with failure probability.

General Entropy -

Ps - probability of success. calculated by multiplication of component success ( 1 - component failure).
Pf - probability of failure. 1 - Ps.
Es - entropy of success: use analyzer code to obtain component new probability given success state.
Pf - entropy of failure: use analyzer code to obtain component new probability given failure state.

Algorithm:

Given X as the max amount of tests.

on each round find the min on each test Ps * Es + Pf * Ef.

perform the test.

do for others until X tests selected.



Analyzer input file example:

[Description]
bla bla bla
[Components names]
[(0,'a'),(1,'b'),(2,'c'),(3,'d')]
[Priors]
[0.1,0.1,0.1,0.1]
[Bugs]
[0]
[InitialTests]
['T1','T2','T3','T4']
[TestDetails]
T1;[0,2,3];1
T2;[2];1
T3;[0,1,2];1
T4;[0,1,3];0