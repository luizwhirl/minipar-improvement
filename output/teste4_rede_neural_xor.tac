func sigmoid:
t0 = 0 - x
param t0
t1 = call exp, 1
t2 = 1 + t1
t3 = 1 / t2
return t3
endfunc sigmoid
print "Input: [0, 0], Predicted Output: 0.0089"
print "Input: [0, 1], Predicted Output: 0.9769"
print "Input: [1, 0], Predicted Output: 0.9758"
print "Input: [1, 1], Predicted Output: 0.0291"
