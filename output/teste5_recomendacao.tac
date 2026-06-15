func relu:
t0 = x > 0
ifFalse t0 goto ENDIF_0
return x
ENDIF_0:
return 0.0
endfunc relu
func sigmoid:
t1 = 0 - x
param t1
t2 = call exp, 1
t3 = 1 + t2
t4 = 1 / t3
return t4
endfunc sigmoid
func peso_entrada_oculta:
t5 = produto + 1
t6 = neuronio + 2
t7 = t5 * t6
t8 = t7 % 7
base = t8
t9 = base + 1
t10 = t9 / 20.0
return t10
endfunc peso_entrada_oculta
func bias_oculto:
t11 = neuronio % 3
t12 = t11 / 20.0
return t12
endfunc bias_oculto
func peso_oculta_saida:
t13 = neuronio + 3
t14 = produto + 1
t15 = t13 * t14
t16 = t15 % 5
base = t16
t17 = base + 1
t18 = t17 / 25.0
return t18
endfunc peso_oculta_saida
func bias_saida:
t19 = historico[produto]
t20 = t19 == 1
ifFalse t20 goto ENDIF_1
t21 = -0.25
return t21
ENDIF_1:
t22 = -0.10
return t22
endfunc bias_saida
func nome_produto:
t23 = indice == 0
ifFalse t23 goto ENDIF_2
return "Smartphone"
ENDIF_2:
t24 = indice == 1
ifFalse t24 goto ENDIF_3
return "Laptop"
ENDIF_3:
t25 = indice == 2
ifFalse t25 goto ENDIF_4
return "Tablet"
ENDIF_4:
t26 = indice == 3
ifFalse t26 goto ENDIF_5
return "Fones de ouvido"
ENDIF_5:
t27 = indice == 4
ifFalse t27 goto ENDIF_6
return "Camisa"
ENDIF_6:
t28 = indice == 5
ifFalse t28 goto ENDIF_7
return "Jeans"
ENDIF_7:
t29 = indice == 6
ifFalse t29 goto ENDIF_8
return "Jaqueta"
ENDIF_8:
t30 = indice == 7
ifFalse t30 goto ENDIF_9
return "Sapatos"
ENDIF_9:
t31 = indice == 8
ifFalse t31 goto ENDIF_10
return "Geladeira"
ENDIF_10:
t32 = indice == 9
ifFalse t32 goto ENDIF_11
return "Micro-ondas"
ENDIF_11:
t33 = indice == 10
ifFalse t33 goto ENDIF_12
return "Maquina de lavar"
ENDIF_12:
t34 = indice == 11
ifFalse t34 goto ENDIF_13
return "Ar condicionado"
ENDIF_13:
t35 = indice == 12
ifFalse t35 goto ENDIF_14
return "Ficcao"
ENDIF_14:
t36 = indice == 13
ifFalse t36 goto ENDIF_15
return "Nao-ficcao"
ENDIF_15:
t37 = indice == 14
ifFalse t37 goto ENDIF_16
return "Ficcao cientifica"
ENDIF_16:
return "Fantasia"
endfunc nome_produto
# class Usuario
func codificar_historico:
t38 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0]
return t38
endfunc codificar_historico
# class RedeNeuralRecomendacao
func forward:
t39 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
ocultas = t39
t40 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
saidas = t40
h = 0
WHILE_17:
t41 = this.hidden_size
t42 = h < t41
ifFalse t42 goto ENDWHILE_18
soma_oculta = 0.0
entrada = 0
WHILE_19:
t43 = this.input_size
t44 = entrada < t43
ifFalse t44 goto ENDWHILE_20
t45 = historico[entrada]
param entrada
param h
t46 = call peso_entrada_oculta, 2
t47 = t45 * t46
t48 = soma_oculta + t47
soma_oculta = t48
t49 = entrada + 1
entrada = t49
goto WHILE_19
ENDWHILE_20:
param h
t50 = call bias_oculto, 1
t51 = soma_oculta + t50
param t51
t52 = call relu, 1
ocultas[h] = t52
t53 = h + 1
h = t53
goto WHILE_17
ENDWHILE_18:
produto = 0
WHILE_21:
t54 = this.output_size
t55 = produto < t54
ifFalse t55 goto ENDWHILE_22
soma_saida = 0.0
neuronio = 0
WHILE_23:
t56 = this.hidden_size
t57 = neuronio < t56
ifFalse t57 goto ENDWHILE_24
t58 = ocultas[neuronio]
param neuronio
param produto
t59 = call peso_oculta_saida, 2
t60 = t58 * t59
t61 = soma_saida + t60
soma_saida = t61
t62 = neuronio + 1
neuronio = t62
goto WHILE_23
ENDWHILE_24:
param produto
param historico
t63 = call bias_saida, 2
t64 = soma_saida + t63
param t64
t65 = call sigmoid, 1
saidas[produto] = t65
t66 = produto + 1
produto = t66
goto WHILE_21
ENDWHILE_22:
return saidas
endfunc forward
# class Recomendador
func recomendar:
t67 = new Usuario
usuario = t67
t68 = new RedeNeuralRecomendacao
rede = t68
t69 = call usuario.codificar_historico, 0
historico = t69
param historico
t70 = call rede.forward, 1
probabilidades = t70
print "==== Teste 5: recomendacao e-commerce com rede neural ===="
print "Produtos recomendados para voce:"
produto = 0
WHILE_25:
t71 = produto < 16
ifFalse t71 goto ENDWHILE_26
t72 = historico[produto]
t73 = t72 == 0
t74 = probabilidades[produto]
t75 = t74 > 0.55
t76 = t73 && t75
ifFalse t76 goto ENDIF_27
param produto
t77 = call nome_produto, 1
print t77
print "probabilidade:"
t78 = probabilidades[produto]
print t78
ENDIF_27:
t79 = produto + 1
produto = t79
goto WHILE_25
ENDWHILE_26:
endfunc recomendar
t80 = new Recomendador
recomendador = t80
t81 = call recomendador.recomendar, 0
