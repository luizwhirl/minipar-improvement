func sigmoid:
t0 = 0 - x
param t0
t1 = call exp, 1
t2 = 1 + t1
t3 = 1 / t2
return t3
endfunc sigmoid
func sigmoid_deriv:
t4 = 1 - x
t5 = x * t4
return t5
endfunc sigmoid_deriv
# class Neuronio
func init:
this.p0 = w0
this.p1 = w1
this.bias_val = b
this.saida = 0
endfunc init
func feedforward2:
t6 = this.p0
t7 = e0 * t6
t8 = this.p1
t9 = e1 * t8
t10 = t7 + t9
t11 = this.bias_val
t12 = t10 + t11
soma = t12
param soma
t13 = call sigmoid, 1
this.saida = t13
t14 = this.saida
return t14
endfunc feedforward2
func feedforward3:
t15 = this.p0
t16 = e0 * t15
t17 = this.p1
t18 = e1 * t17
t19 = t16 + t18
t20 = this.bias_val
t21 = e2 * t20
t22 = t19 + t21
soma = t22
param soma
t23 = call sigmoid, 1
this.saida = t23
t24 = this.saida
return t24
endfunc feedforward3
# class RedeNeural
func inicializar:
t25 = new Neuronio
this.n0 = t25
t26 = new Neuronio
this.n1 = t26
t27 = new Neuronio
this.n2 = t27
t28 = new Neuronio
this.ns = t28
t29 = this.n0
param 0.5
param 0.5
param 0.5
t30 = call t29.init, 3
t31 = this.n1
param 0.5
param 0.5
param 0.5
t32 = call t31.init, 3
t33 = this.n2
param 0.5
param 0.5
param 0.5
t34 = call t33.init, 3
t35 = this.ns
param 0.5
param 0.5
param 0.5
t36 = call t35.init, 3
endfunc inicializar
func forward:
t37 = this.n0
param e0
param e1
t38 = call t37.feedforward2, 2
o0 = t38
t39 = this.n1
param e0
param e1
t40 = call t39.feedforward2, 2
o1 = t40
t41 = this.n2
param e0
param e1
t42 = call t41.feedforward2, 2
o2 = t42
t43 = this.ns
param o0
param o1
param o2
t44 = call t43.feedforward3, 3
out = t44
return out
endfunc forward
func treinar_amostra:
t45 = this.n0
param e0
param e1
t46 = call t45.feedforward2, 2
o0 = t46
t47 = this.n1
param e0
param e1
t48 = call t47.feedforward2, 2
o1 = t48
t49 = this.n2
param e0
param e1
t50 = call t49.feedforward2, 2
o2 = t50
t51 = this.ns
param o0
param o1
param o2
t52 = call t51.feedforward3, 3
out = t52
t53 = alvo - out
erro = t53
param out
t54 = call sigmoid_deriv, 1
t55 = erro * t54
delta_s = t55
t56 = this.ns
t58 = this.ns
t57 = t58.p0
t59 = o0 * delta_s
t60 = this.taxa
t61 = t59 * t60
t62 = t57 + t61
t56.p0 = t62
t63 = this.ns
t65 = this.ns
t64 = t65.p1
t66 = o1 * delta_s
t67 = this.taxa
t68 = t66 * t67
t69 = t64 + t68
t63.p1 = t69
t70 = this.ns
t72 = this.ns
t71 = t72.bias_val
t73 = this.taxa
t74 = delta_s * t73
t75 = t71 + t74
t70.bias_val = t75
t77 = this.ns
t76 = t77.p0
t78 = delta_s * t76
param o0
t79 = call sigmoid_deriv, 1
t80 = t78 * t79
d0 = t80
t82 = this.ns
t81 = t82.p1
t83 = delta_s * t81
param o1
t84 = call sigmoid_deriv, 1
t85 = t83 * t84
d1 = t85
t87 = this.ns
t86 = t87.bias_val
t88 = delta_s * t86
param o2
t89 = call sigmoid_deriv, 1
t90 = t88 * t89
d2 = t90
t91 = this.n0
t93 = this.n0
t92 = t93.p0
t94 = e0 * d0
t95 = this.taxa
t96 = t94 * t95
t97 = t92 + t96
t91.p0 = t97
t98 = this.n0
t100 = this.n0
t99 = t100.p1
t101 = e1 * d0
t102 = this.taxa
t103 = t101 * t102
t104 = t99 + t103
t98.p1 = t104
t105 = this.n0
t107 = this.n0
t106 = t107.bias_val
t108 = this.taxa
t109 = d0 * t108
t110 = t106 + t109
t105.bias_val = t110
t111 = this.n1
t113 = this.n1
t112 = t113.p0
t114 = e0 * d1
t115 = this.taxa
t116 = t114 * t115
t117 = t112 + t116
t111.p0 = t117
t118 = this.n1
t120 = this.n1
t119 = t120.p1
t121 = e1 * d1
t122 = this.taxa
t123 = t121 * t122
t124 = t119 + t123
t118.p1 = t124
t125 = this.n1
t127 = this.n1
t126 = t127.bias_val
t128 = this.taxa
t129 = d1 * t128
t130 = t126 + t129
t125.bias_val = t130
t131 = this.n2
t133 = this.n2
t132 = t133.p0
t134 = e0 * d2
t135 = this.taxa
t136 = t134 * t135
t137 = t132 + t136
t131.p0 = t137
t138 = this.n2
t140 = this.n2
t139 = t140.p1
t141 = e1 * d2
t142 = this.taxa
t143 = t141 * t142
t144 = t139 + t143
t138.p1 = t144
t145 = this.n2
t147 = this.n2
t146 = t147.bias_val
t148 = this.taxa
t149 = d2 * t148
t150 = t146 + t149
t145.bias_val = t150
endfunc treinar_amostra
func treinar_epocas:
ep = 0
WHILE_0:
t151 = ep < epocas
ifFalse t151 goto ENDWHILE_1
param 0
param 0
param 0
t152 = call this.treinar_amostra, 3
param 0
param 1
param 1
t153 = call this.treinar_amostra, 3
param 1
param 0
param 1
t154 = call this.treinar_amostra, 3
param 1
param 1
param 0
t155 = call this.treinar_amostra, 3
t156 = ep + 1
ep = t156
goto WHILE_0
ENDWHILE_1:
endfunc treinar_epocas
print "=== Rede Neural XOR - MiniPar 2026.1 ==="
print "--- Treinando Rede Neural XOR ---"
print "Epocas: 20000"
t157 = new RedeNeural
rede = t157
t158 = call rede.inicializar, 0
param 20000
t159 = call rede.treinar_epocas, 1
print "Treinamento concluido"
print "--- Testando Rede Neural ---"
param 0
param 0
t160 = call rede.forward, 2
r00 = t160
print "Input: [0, 0], Predicted Output:"
print r00
param 0
param 1
t161 = call rede.forward, 2
r01 = t161
print "Input: [0, 1], Predicted Output:"
print r01
param 1
param 0
t162 = call rede.forward, 2
r10 = t162
print "Input: [1, 0], Predicted Output:"
print r10
param 1
param 1
t163 = call rede.forward, 2
r11 = t163
print "Input: [1, 1], Predicted Output:"
print r11
