# bgu-aitesting-testoptimizer

Project for finding optimal sub set of test that will give the max bugs using Information gain.

Each test have component with failure probability.

General Entropy -

Ps - probability of success.
Pf - probability of failure.
Es - entropy of success.
Pf - entropy of failure.

Algorithm:

on each round find the min on each test.

Ps * Es + Pf * Ef

use analyzer code to obtain component new probability given state.

perform the test.

do for others until X tests selected.