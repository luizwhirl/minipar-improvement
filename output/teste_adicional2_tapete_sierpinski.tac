func preencher:
t0 = tamanho == 1
ifFalse t0 goto ENDIF_0
t1 = tela[linha]
t1[coluna] = "#"
return tela
ENDIF_0:
t2 = tamanho / 3
novo = t2
i = 0
WHILE_1:
t3 = i < 3
ifFalse t3 goto ENDWHILE_2
j = 0
WHILE_3:
t4 = j < 3
ifFalse t4 goto ENDWHILE_4
t5 = i == 1
t6 = j == 1
t7 = t5 && t6
t8 = !t7
ifFalse t8 goto ENDIF_5
param tela
t9 = i * novo
t10 = linha + t9
param t10
t11 = j * novo
t12 = coluna + t11
param t12
param novo
t13 = call preencher, 4
tela = t13
ENDIF_5:
t14 = j + 1
j = t14
goto WHILE_3
ENDWHILE_4:
t15 = i + 1
i = t15
goto WHILE_1
ENDWHILE_2:
return tela
endfunc preencher
tamanho = 9
t16 = matrix(tamanho, tamanho, " ")
tela = t16
param tela
param 0
param 0
param tamanho
t17 = call preencher, 4
tela = t17
i = 0
WHILE_6:
t18 = i < tamanho
ifFalse t18 goto ENDWHILE_7
t19 = tela[i]
print t19
t20 = i + 1
i = t20
goto WHILE_6
ENDWHILE_7:
