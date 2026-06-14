# class Quicksort
func trocar:
t1 = this.array
t0 = t1[i]
temp = t0
t2 = this.array
t4 = this.array
t3 = t4[j]
t2[i] = t3
t5 = this.array
t5[j] = temp
endfunc trocar
func particionar:
t7 = this.array
t6 = t7[fim]
pivot = t6
t8 = inicio - 1
i = t8
j = inicio
WHILE_0:
t9 = j < fim
ifFalse t9 goto ENDWHILE_1
t11 = this.array
t10 = t11[j]
t12 = t10 <= pivot
ifFalse t12 goto ENDIF_2
t13 = i + 1
i = t13
param i
param j
t14 = call this.trocar, 2
ENDIF_2:
t15 = j + 1
j = t15
goto WHILE_0
ENDWHILE_1:
t16 = i + 1
i = t16
param i
param fim
t17 = call this.trocar, 2
return i
endfunc particionar
func quicksort:
t18 = inicio < fim
ifFalse t18 goto ENDIF_3
param inicio
param fim
t19 = call this.particionar, 2
p = t19
param inicio
t20 = p - 1
param t20
t21 = call this.quicksort, 2
t22 = p + 1
param t22
param fim
t23 = call this.quicksort, 2
ENDIF_3:
endfunc quicksort
func ordenar:
param 0
param 5
t24 = call this.quicksort, 2
t25 = this.array
return t25
endfunc ordenar
print "==== Ordenação com Quicksort ===="
print "Insira os elementos do vetor separados por espaço:"
print "10 -3 -40 80 70 -100"
t26 = new Quicksort
algoritmo = t26
print "Vetor original: [10, -3, -40, 80, 70, -100]"
t27 = call algoritmo.ordenar, 0
vetor_ordenado = t27
print "Vetor ordenado:"
print vetor_ordenado
