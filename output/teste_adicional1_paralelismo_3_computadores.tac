func quicksort_resumo:
return "PC1 QuickSort: [33,12,98,5,61] -> [5,12,33,61,98]"
endfunc quicksort_resumo
func matrizes_resumo:
return "PC2 Matrizes: [[1,2],[3,4]] x [[5,6],[7,8]] -> [[19,22],[43,50]]"
endfunc matrizes_resumo
func fatorial_resumo:
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
return "PC3 Fatorial: 5! = 120"
endfunc fatorial_resumo
print "==== Teste adicional 1: paralelismo real com 3 computadores ===="
print "Menu do Computador 1"
print "1 - Quick sort no Computador 1: 127.0.0.1:5301"
print "2 - Multiplicacao de matrizes no Computador 2: 127.0.0.1:5302"
print "3 - Fatorial no Computador 3: 127.0.0.1:5303"
t3 = c_channel("127.0.0.1", 5301)
canal_pc1 = t3
t4 = c_channel("127.0.0.1", 5302)
canal_pc2 = t4
t5 = c_channel("127.0.0.1", 5303)
canal_pc3 = t5
t6 = receive canal_pc1
resultado1 = t6
t7 = receive canal_pc2
resultado2 = t7
t8 = receive canal_pc3
resultado3 = t8
print "Resultados recolhidos no Computador 1:"
print resultado1
print resultado2
print resultado3
t9 = call quicksort_resumo, 0
send canal_pc1, t9
t10 = call matrizes_resumo, 0
send canal_pc2, t10
t11 = call fatorial_resumo, 0
send canal_pc3, t11
