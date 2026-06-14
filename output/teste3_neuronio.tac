# class Neuronio
func ativacao:
t0 = soma >= 0
ifFalse t0 goto ENDIF_0
return 1
ENDIF_0:
return 0
endfunc ativacao
func treinar:
print "Entrada:"
t1 = this.input_val
print t1
print "| Saida desejada:"
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
print "#### Iteracao:"
t17 = this.iteracao
print t17
print "Peso:"
t18 = this.peso
print t18
print "Saida:"
print saida
print "Erro:"
t19 = this.erro
print t19
t20 = this.erro
t21 = t20 != 0
ifFalse t21 goto ENDIF_3
t22 = this.peso
t23 = this.taxa_aprendizado
t24 = this.input_val
t25 = t23 * t24
t26 = this.erro
t27 = t25 * t26
t28 = t22 + t27
this.peso = t28
t29 = this.peso_bias
t30 = this.taxa_aprendizado
t31 = this.bias
t32 = t30 * t31
t33 = this.erro
t34 = t32 * t33
t35 = t29 + t34
this.peso_bias = t35
print "Peso do bias:"
t36 = this.peso_bias
print t36
ENDIF_3:
goto WHILE_1
ENDWHILE_2:
print "Parabens! O neuronio aprendeu."
print "Valor desejado:"
t37 = this.output_desejado
print t37
endfunc treinar
t38 = new Neuronio
neuronio = t38
t39 = call neuronio.treinar, 0
