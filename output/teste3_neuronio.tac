# class Neuronio
func ativacao:
t0 = soma > 0
ifFalse t0 goto ENDIF_0
return 1
ENDIF_0:
return 0
endfunc ativacao
func treinar:
print "==== Teste 3: neuronio simples com classes e objetos ===="
print "Entrada:"
t1 = this.input_val
print t1
print "Saida desejada:"
t2 = this.output_desejado
print t2
WHILE_1:
t3 = this.erro
t4 = t3 != 0
ifFalse t4 goto ENDWHILE_2
t5 = this.iteracao
t6 = t5 + 1
this.iteracao = t6
t7 = this.input_val
t8 = this.peso
t9 = t7 * t8
t10 = this.bias
t11 = this.peso_bias
t12 = t10 * t11
t13 = t9 + t12
soma = t13
param soma
t14 = call this.ativacao, 1
saida = t14
t15 = this.output_desejado
t16 = t15 - saida
this.erro = t16
print "Iteracao:"
t17 = this.iteracao
print t17
print "Soma ponderada:"
print soma
print "Saida:"
print saida
print "Erro:"
t18 = this.erro
print t18
print "Peso entrada:"
t19 = this.peso
print t19
print "Peso bias:"
t20 = this.peso_bias
print t20
t21 = this.erro
t22 = t21 != 0
ifFalse t22 goto ENDIF_3
t23 = this.peso
t24 = this.taxa_aprendizado
t25 = this.input_val
t26 = t24 * t25
t27 = this.erro
t28 = t26 * t27
t29 = t23 + t28
this.peso = t29
t30 = this.peso_bias
t31 = this.taxa_aprendizado
t32 = this.bias
t33 = t31 * t32
t34 = this.erro
t35 = t33 * t34
t36 = t30 + t35
this.peso_bias = t36
ENDIF_3:
goto WHILE_1
ENDWHILE_2:
print "Neuronio aprendeu dinamicamente."
print "Iteracoes totais:"
t37 = this.iteracao
print t37
print "Peso final:"
t38 = this.peso
print t38
print "Peso bias final:"
t39 = this.peso_bias
print t39
print "Valor desejado:"
t40 = this.output_desejado
print t40
endfunc treinar
t41 = new Neuronio
neuronio = t41
t42 = call neuronio.treinar, 0
