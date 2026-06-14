func ler_nome:
t0 = input("Nome: ")
nome = t0
return nome
endfunc ler_nome
soma = 0
i = 0
FOR_0:
t1 = i < 5
ifFalse t1 goto ENDFOR_2
t2 = i == 3
ifFalse t2 goto ENDIF_3
goto FOR_STEP_1
ENDIF_3:
t3 = soma + i
soma = t3
FOR_STEP_1:
t4 = i + 1
i = t4
goto FOR_0
ENDFOR_2:
tentativas = 0
DO_4:
t5 = tentativas + 1
tentativas = t5
t6 = tentativas == 2
ifFalse t6 goto ENDIF_6
goto ENDDO_5
ENDIF_6:
t7 = tentativas < 10
if t7 goto DO_4
ENDDO_5:
print "Controle OK:"
print soma
print tentativas
