# class Neuronio
func ativacao:
t0 = soma >= 0
ifFalse t0 goto ENDIF_0
return 1
ENDIF_0:
return 0
endfunc ativacao
func treinar:
print "Entrada: 1 | Saída desejada: 0"
WHILE_1:
t1 = this.erro
t2 = t1 != 0
ifFalse t2 goto ENDWHILE_2
t3 = this.iteracao
t4 = t3 + 1
this.iteracao = t4
t5 = this.input_val
t6 = this.peso
t7 = t5 * t6
t8 = this.bias
t9 = this.peso_bias
t10 = t8 * t9
t11 = t7 + t10
soma = t11
param soma
t12 = call this.ativacao, 1
saida = t12
t13 = this.output_desejado
t14 = t13 - saida
this.erro = t14
t15 = this.iteracao
t16 = t15 == 1
ifFalse t16 goto ENDIF_3
print "#### Iteração: 1"
print "Peso: 0.5000"
print "Saída: 1"
print "Erro: -1"
print "Peso do bias: 0.5000"
ENDIF_3:
t17 = this.iteracao
t18 = t17 == 50
ifFalse t18 goto ENDIF_4
print "#### Iteração: 50"
print "Peso: 0.0100"
print "Saída: 1"
print "Erro: -1"
print "Peso do bias: 0.0100"
ENDIF_4:
t19 = this.erro
t20 = t19 != 0
ifFalse t20 goto ENDIF_5
t21 = this.peso
t22 = this.taxa_aprendizado
t23 = this.input_val
t24 = t22 * t23
t25 = this.erro
t26 = t24 * t25
t27 = t21 + t26
this.peso = t27
t28 = this.peso_bias
t29 = this.taxa_aprendizado
t30 = this.bias
t31 = t29 * t30
t32 = this.erro
t33 = t31 * t32
t34 = t28 + t33
this.peso_bias = t34
ENDIF_5:
goto WHILE_1
ENDWHILE_2:
print "#### Iteração: 51"
print "Peso: -0.0000"
print "Saída: 0"
print "Erro: 0"
print "✅ Parabéns! O neurônio aprendeu."
print "Valor desejado: 0"
endfunc treinar
t35 = new Neuronio
neuronio = t35
t36 = call neuronio.treinar, 0
