t0 = c_channel("127.0.0.1", 5201)
pc1 = t0
t1 = c_channel("127.0.0.1", 5202)
pc2 = t1
t2 = c_channel("127.0.0.1", 5203)
pc3 = t2
send pc1, "PC1 QuickSort: [33,12,98,5,61] -> [5,12,33,61,98]"
send pc2, "PC2 Matrizes: [[1,2],[3,4]] x [[5,6],[7,8]] -> [[19,22],[43,50]]"
send pc3, "PC3 Fatorial: 5! = 120"
