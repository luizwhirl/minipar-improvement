func sigmoid:
t0 = 0 - x
param t0
t1 = call exp, 1
t2 = 1 + t1
t3 = 1 / t2
return t3
endfunc sigmoid
func derivada_sigmoid:
t4 = 1 - saida
t5 = saida * t4
return t5
endfunc derivada_sigmoid
# class RedeNeuralXOR
func feedforward:
t6 = this.h1_w1
t7 = x1 * t6
t8 = this.h1_w2
t9 = x2 * t8
t10 = t7 + t9
t11 = this.h1_bias
t12 = t10 + t11
param t12
t13 = call sigmoid, 1
this.h1 = t13
t14 = this.h2_w1
t15 = x1 * t14
t16 = this.h2_w2
t17 = x2 * t16
t18 = t15 + t17
t19 = this.h2_bias
t20 = t18 + t19
param t20
t21 = call sigmoid, 1
this.h2 = t21
t22 = this.h3_w1
t23 = x1 * t22
t24 = this.h3_w2
t25 = x2 * t24
t26 = t23 + t25
t27 = this.h3_bias
t28 = t26 + t27
param t28
t29 = call sigmoid, 1
this.h3 = t29
t30 = this.h1
t31 = this.out_w1
t32 = t30 * t31
t33 = this.h2
t34 = this.out_w2
t35 = t33 * t34
t36 = t32 + t35
t37 = this.h3
t38 = this.out_w3
t39 = t37 * t38
t40 = t36 + t39
t41 = this.out_bias
t42 = t40 + t41
param t42
t43 = call sigmoid, 1
this.saida = t43
t44 = this.saida
return t44
endfunc feedforward
func treinar_amostra:
param x1
param x2
t45 = call this.feedforward, 2
previsto = t45
t46 = desejado - previsto
erro = t46
param previsto
t47 = call derivada_sigmoid, 1
t48 = erro * t47
delta_saida = t48
t49 = this.out_w1
antigo_out_w1 = t49
t50 = this.out_w2
antigo_out_w2 = t50
t51 = this.out_w3
antigo_out_w3 = t51
t52 = this.out_w1
t53 = this.h1
t54 = t53 * delta_saida
t55 = this.taxa_aprendizado
t56 = t54 * t55
t57 = t52 + t56
this.out_w1 = t57
t58 = this.out_w2
t59 = this.h2
t60 = t59 * delta_saida
t61 = this.taxa_aprendizado
t62 = t60 * t61
t63 = t58 + t62
this.out_w2 = t63
t64 = this.out_w3
t65 = this.h3
t66 = t65 * delta_saida
t67 = this.taxa_aprendizado
t68 = t66 * t67
t69 = t64 + t68
this.out_w3 = t69
t70 = this.out_bias
t71 = this.taxa_aprendizado
t72 = delta_saida * t71
t73 = t70 + t72
this.out_bias = t73
t74 = delta_saida * antigo_out_w1
t75 = this.h1
param t75
t76 = call derivada_sigmoid, 1
t77 = t74 * t76
delta_h1 = t77
t78 = delta_saida * antigo_out_w2
t79 = this.h2
param t79
t80 = call derivada_sigmoid, 1
t81 = t78 * t80
delta_h2 = t81
t82 = delta_saida * antigo_out_w3
t83 = this.h3
param t83
t84 = call derivada_sigmoid, 1
t85 = t82 * t84
delta_h3 = t85
t86 = this.h1_w1
t87 = x1 * delta_h1
t88 = this.taxa_aprendizado
t89 = t87 * t88
t90 = t86 + t89
this.h1_w1 = t90
t91 = this.h1_w2
t92 = x2 * delta_h1
t93 = this.taxa_aprendizado
t94 = t92 * t93
t95 = t91 + t94
this.h1_w2 = t95
t96 = this.h1_bias
t97 = this.taxa_aprendizado
t98 = delta_h1 * t97
t99 = t96 + t98
this.h1_bias = t99
t100 = this.h2_w1
t101 = x1 * delta_h2
t102 = this.taxa_aprendizado
t103 = t101 * t102
t104 = t100 + t103
this.h2_w1 = t104
t105 = this.h2_w2
t106 = x2 * delta_h2
t107 = this.taxa_aprendizado
t108 = t106 * t107
t109 = t105 + t108
this.h2_w2 = t109
t110 = this.h2_bias
t111 = this.taxa_aprendizado
t112 = delta_h2 * t111
t113 = t110 + t112
this.h2_bias = t113
t114 = this.h3_w1
t115 = x1 * delta_h3
t116 = this.taxa_aprendizado
t117 = t115 * t116
t118 = t114 + t117
this.h3_w1 = t118
t119 = this.h3_w2
t120 = x2 * delta_h3
t121 = this.taxa_aprendizado
t122 = t120 * t121
t123 = t119 + t122
this.h3_w2 = t123
t124 = this.h3_bias
t125 = this.taxa_aprendizado
t126 = delta_h3 * t125
t127 = t124 + t126
this.h3_bias = t127
endfunc treinar_amostra
func treinar:
epoca = 0
WHILE_0:
t128 = epoca < 20000
ifFalse t128 goto ENDWHILE_1
param 0
param 0
param 0
t129 = call this.treinar_amostra, 3
param 0
param 1
param 1
t130 = call this.treinar_amostra, 3
param 1
param 0
param 1
t131 = call this.treinar_amostra, 3
param 1
param 1
param 0
t132 = call this.treinar_amostra, 3
t133 = epoca + 1
epoca = t133
goto WHILE_0
ENDWHILE_1:
endfunc treinar
func testar:
print "==== Teste 4: rede neural XOR com backpropagation ===="
print "Input: [0, 0], Predicted Output:"
param 0
param 0
t134 = call this.feedforward, 2
print t134
print "Input: [0, 1], Predicted Output:"
param 0
param 1
t135 = call this.feedforward, 2
print t135
print "Input: [1, 0], Predicted Output:"
param 1
param 0
t136 = call this.feedforward, 2
print t136
print "Input: [1, 1], Predicted Output:"
param 1
param 1
t137 = call this.feedforward, 2
print t137
endfunc testar
t138 = new RedeNeuralXOR
rede = t138
t139 = call rede.treinar, 0
t140 = call rede.testar, 0
