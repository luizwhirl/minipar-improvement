print "========================================"
print "  FRACTAL DE SIERPINSKI (Automato)      "
print "========================================"
linhas = 32
colunas = 64
t0 = matrix(linhas, colunas, " ")
tela = t0
t1 = matrix(linhas, colunas, 0)
controle = t1
meio = 31
t2 = controle[0]
t2[meio] = 1
t3 = tela[0]
t3[meio] = "A"
i = 1
WHILE_0:
t4 = i < linhas
ifFalse t4 goto ENDWHILE_1
j = 1
WHILE_2:
t5 = colunas - 1
t6 = j < t5
ifFalse t6 goto ENDWHILE_3
t9 = i - 1
t8 = controle[t9]
t10 = j - 1
t7 = t8[t10]
esq = t7
t13 = i - 1
t12 = controle[t13]
t14 = j + 1
t11 = t12[t14]
dir = t11
t15 = esq + dir
t16 = t15 == 1
ifFalse t16 goto ENDIF_4
t17 = controle[i]
t17[j] = 1
t18 = tela[i]
t18[j] = "A"
ENDIF_4:
t19 = j + 1
j = t19
goto WHILE_2
ENDWHILE_3:
t20 = i + 1
i = t20
goto WHILE_0
ENDWHILE_1:
print "Calculo finalizado. Renderizando..."
k = 0
WHILE_5:
t21 = k < linhas
ifFalse t21 goto ENDWHILE_6
t22 = tela[k]
print t22
t23 = k + 1
k = t23
goto WHILE_5
ENDWHILE_6:
print "========================================"
