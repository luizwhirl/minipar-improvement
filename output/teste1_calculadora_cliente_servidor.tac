print "==== Calculadora cliente-servidor ===="
t0 = c_channel("127.0.0.1", 5101)
requisicao = t0
t1 = c_channel("127.0.0.1", 5102)
resposta = t1
t2 = receive requisicao
pedido = t2
print "Servidor recebeu:"
print pedido
send resposta, "Resultado: 12"
send requisicao, "+ 7 5"
t3 = receive resposta
resultado = t3
print resultado
