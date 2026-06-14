n = 5
fat = 1
i = 1
WHILE_0:
t0 = i <= n
ifFalse t0 goto ENDWHILE_1
t1 = fat * i
fat = t1
t2 = i + 1
i = t2
goto WHILE_0
ENDWHILE_1:
print "Fatorial de 5:"
print fat
limite = 8
a = 0
b = 1
i = 0
print "Fibonacci:"
WHILE_2:
t3 = i < limite
ifFalse t3 goto ENDWHILE_3
print a
t4 = a + b
prox = t4
a = b
b = prox
t5 = i + 1
i = t5
goto WHILE_2
ENDWHILE_3:
