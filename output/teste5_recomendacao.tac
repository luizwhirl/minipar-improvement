func relu:
t0 = x > 0
ifFalse t0 goto ENDIF_0
return x
ENDIF_0:
return 0
endfunc relu
func sigmoid:
t1 = 0 - x
param t1
t2 = call exp, 1
t3 = 1 + t2
t4 = 1 / t3
return t4
endfunc sigmoid
# class Produto
func definir:
this.nome = n
endfunc definir
# class RedeNeural
func definir_tam:
this.tam = t
endfunc definir_tam
func oculto:
soma = 0
j = 0
WHILE_1:
t5 = this.tam
t6 = j < t5
ifFalse t6 goto ENDWHILE_2
t7 = historico[j]
t8 = this.peso
t9 = t7 * t8
t10 = soma + t9
soma = t10
t11 = j + 1
j = t11
goto WHILE_1
ENDWHILE_2:
t12 = this.bias_oculto
t13 = soma + t12
soma = t13
param soma
t14 = call relu, 1
return t14
endfunc oculto
func saida:
t15 = this.peso
t16 = ativ_oculta * t15
t17 = this.bias_saida
t18 = t16 + t17
soma = t18
param soma
t19 = call sigmoid, 1
return t19
endfunc saida
func forward:
ativ = 0
h = 0
WHILE_3:
t20 = this.neuronios_ocultos
t21 = h < t20
ifFalse t21 goto ENDWHILE_4
param historico
param h
t22 = call this.oculto, 2
t23 = ativ + t22
ativ = t23
t24 = h + 1
h = t24
goto WHILE_3
ENDWHILE_4:
t25 = this.neuronios_ocultos
t26 = ativ / t25
media_oculta = t26
i = 0
WHILE_5:
t27 = this.tam
t28 = i < t27
ifFalse t28 goto ENDWHILE_6
param media_oculta
param i
t29 = call this.saida, 2
resultado[i] = t29
t30 = i + 1
i = t30
goto WHILE_5
ENDWHILE_6:
return resultado
endfunc forward
t31 = new Produto
p0 = t31
param "Smartphone"
t32 = call p0.definir, 1
t33 = new Produto
p1 = t33
param "Laptop"
t34 = call p1.definir, 1
t35 = new Produto
p2 = t35
param "Tablet"
t36 = call p2.definir, 1
t37 = new Produto
p3 = t37
param "Fones de ouvido"
t38 = call p3.definir, 1
t39 = new Produto
p4 = t39
param "Camisa"
t40 = call p4.definir, 1
t41 = new Produto
p5 = t41
param "Jeans"
t42 = call p5.definir, 1
t43 = new Produto
p6 = t43
param "Jaqueta"
t44 = call p6.definir, 1
t45 = new Produto
p7 = t45
param "Sapatos"
t46 = call p7.definir, 1
t47 = new Produto
p8 = t47
param "Geladeira"
t48 = call p8.definir, 1
t49 = new Produto
p9 = t49
param "Micro-ondas"
t50 = call p9.definir, 1
t51 = new Produto
p10 = t51
param "Maquina de lavar"
t52 = call p10.definir, 1
t53 = new Produto
p11 = t53
param "Ar condicionado"
t54 = call p11.definir, 1
t55 = new Produto
p12 = t55
param "Ficcao"
t56 = call p12.definir, 1
t57 = new Produto
p13 = t57
param "Nao-ficcao"
t58 = call p13.definir, 1
t59 = new Produto
p14 = t59
param "Ficcao cientifica"
t60 = call p14.definir, 1
t61 = new Produto
p15 = t61
param "Fantasia"
t62 = call p15.definir, 1
t63 = ["Smartphone", "Laptop", "Tablet", "Fones de ouvido", "Camisa", "Jeans", "Jaqueta", "Sapatos", "Geladeira", "Micro-ondas", "Maquina de lavar", "Ar condicionado", "Ficcao", "Nao-ficcao", "Ficcao cientifica", "Fantasia"]
nomes = t63
t64 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0]
historico = t64
tam = 16
t65 = new RedeNeural
rede = t65
param tam
t66 = call rede.definir_tam, 1
t67 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
resultado = t67
param historico
param resultado
t68 = call rede.forward, 2
resultado = t68
print "Produtos recomendados para voce:"
i = 0
WHILE_7:
t69 = i < tam
ifFalse t69 goto ENDWHILE_8
t70 = historico[i]
t71 = t70 == 0
ifFalse t71 goto ENDIF_9
t72 = resultado[i]
t73 = t72 > 0.5
ifFalse t73 goto ENDIF_10
t74 = nomes[i]
print t74
ENDIF_10:
ENDIF_9:
t75 = i + 1
i = t75
goto WHILE_7
ENDWHILE_8:
