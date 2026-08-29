function f_00010298(a0, a1, a2)
  local l0
  local S0, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10
  ::BB_00010298:: -- block 0, succs=[53, 1]
  -- init_stack args=3 locals=1
  __ret = f_00096D1B()
  S0 = G[15]
  S1 = true
  S0 = (S0 ~= S1)
  if __is_nil(S0) then goto BB_000104A5 end
  ::BB_000102AA:: -- block 1, succs=[3, 2]
  S0 = a1
  S1 = nil
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_000102B7 end
  ::BB_000102B3:: -- block 2, succs=[3]
  S0 = 1
  a1 = S0
  ::BB_000102B7:: -- block 3, succs=[5, 4]
  S0 = a2
  S1 = nil
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_000102C4 end
  ::BB_000102C0:: -- block 4, succs=[5]
  S0 = 0
  a2 = S0
  ::BB_000102C4:: -- block 5, succs=[11, 6]
  S0 = nil
  a0 = S0
  S0 = G[1950]
  S1 = 0
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_000102F8 end
  ::BB_000102D2:: -- block 6, succs=[8, 7]
  S0 = G[164]
  S1 = 1
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_000102E5 end
  ::BB_000102DD:: -- block 7, succs=[10]
  S0 = nil
  a0 = S0
  goto BB_000102F3
  ::BB_000102E5:: -- block 8, succs=[10, 9]
  S0 = G[164]
  S1 = 2
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_000102F3 end
  ::BB_000102F0:: -- block 9, succs=[10]
  S0 = nil
  a0 = S0
  ::BB_000102F3:: -- block 10, succs=[28]
  goto BB_00010386
  ::BB_000102F8:: -- block 11, succs=[17, 12]
  S0 = G[1950]
  S1 = 1
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010329 end
  ::BB_00010303:: -- block 12, succs=[14, 13]
  S0 = G[164]
  S1 = 1
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010316 end
  ::BB_0001030E:: -- block 13, succs=[16]
  S0 = true
  a0 = S0
  goto BB_00010324
  ::BB_00010316:: -- block 14, succs=[16, 15]
  S0 = G[164]
  S1 = 2
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010324 end
  ::BB_00010321:: -- block 15, succs=[16]
  S0 = nil
  a0 = S0
  ::BB_00010324:: -- block 16, succs=[28]
  goto BB_00010386
  ::BB_00010329:: -- block 17, succs=[23, 18]
  S0 = G[1950]
  S1 = 2
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_0001035A end
  ::BB_00010334:: -- block 18, succs=[20, 19]
  S0 = G[164]
  S1 = 1
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010347 end
  ::BB_0001033F:: -- block 19, succs=[22]
  S0 = nil
  a0 = S0
  goto BB_00010355
  ::BB_00010347:: -- block 20, succs=[22, 21]
  S0 = G[164]
  S1 = 2
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010355 end
  ::BB_00010352:: -- block 21, succs=[22]
  S0 = true
  a0 = S0
  ::BB_00010355:: -- block 22, succs=[28]
  goto BB_00010386
  ::BB_0001035A:: -- block 23, succs=[28, 24]
  S0 = G[1950]
  S1 = 3
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010386 end
  ::BB_00010365:: -- block 24, succs=[26, 25]
  S0 = G[164]
  S1 = 1
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010378 end
  ::BB_00010370:: -- block 25, succs=[28]
  S0 = true
  a0 = S0
  goto BB_00010386
  ::BB_00010378:: -- block 26, succs=[28, 27]
  S0 = G[164]
  S1 = 2
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010386 end
  ::BB_00010383:: -- block 27, succs=[28]
  S0 = true
  a0 = S0
  ::BB_00010386:: -- block 28, succs=[30, 29]
  S0 = G[1227]
  S1 = true
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_0001039E end
  ::BB_00010390:: -- block 29, succs=[30]
  S0 = nil
  G[1227] = S0
  S0 = 1300
  S1 = nil
  S2 = nil
  __ret = f_00055946(S0, S1, S2)
  ::BB_0001039E:: -- block 30, succs=[39, 31]
  S0 = a0
  S1 = nil
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_000103FE end
  ::BB_000103A7:: -- block 31, succs=[35, 32]
  S0 = G[164]
  S1 = 1
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_000103D8 end
  ::BB_000103B2:: -- block 32, succs=[34, 33]
  S0 = a3
  S1 = nil
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_000103C3 end
  ::BB_000103BB:: -- block 33, succs=[34]
  S0 = 450
  S1 = 100
  S0 = (S0 + S1)
  a3 = S0
  ::BB_000103C3:: -- block 34, succs=[38]
  S0 = a2
  S1 = a3
  S2 = nil
  S3 = nil
  S4 = nil
  S5 = nil
  S6 = nil
  S7 = nil
  S8 = nil
  __ret = f_00055D3D(S0, S1, S2, S3, S4, S5, S6, S7, S8)
  goto BB_000103F9
  ::BB_000103D8:: -- block 35, succs=[37, 36]
  S0 = a3
  S1 = nil
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_000103E9 end
  ::BB_000103E1:: -- block 36, succs=[37]
  S0 = 575
  S1 = 100
  S0 = (S0 + S1)
  a3 = S0
  ::BB_000103E9:: -- block 37, succs=[38]
  S0 = a2
  S1 = a3
  S2 = nil
  S3 = nil
  S4 = nil
  S5 = nil
  S6 = nil
  S7 = nil
  S8 = nil
  __ret = f_00055D3D(S0, S1, S2, S3, S4, S5, S6, S7, S8)
  ::BB_000103F9:: -- block 38, succs=[53]
  goto BB_000104A5
  ::BB_000103FE:: -- block 39, succs=[52, 40]
  S0 = a1
  S1 = 1
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010495 end
  ::BB_00010408:: -- block 40, succs=[44, 41]
  S0 = G[14]
  S1 = 1
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_0001043E end
  ::BB_00010413:: -- block 41, succs=[43, 42]
  S0 = a3
  S1 = nil
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010424 end
  ::BB_0001041C:: -- block 42, succs=[43]
  S0 = 450
  S1 = 100
  S0 = (S0 + S1)
  a3 = S0
  ::BB_00010424:: -- block 43, succs=[51]
  S0 = a2
  S1 = a3
  S2 = nil
  S3 = nil
  S4 = nil
  S5 = nil
  S6 = nil
  S7 = nil
  S8 = nil
  __ret = f_00055D3D(S0, S1, S2, S3, S4, S5, S6, S7, S8)
  S0 = 0
  G[14] = S0
  goto BB_00010490
  ::BB_0001043E:: -- block 44, succs=[48, 45]
  S0 = G[164]
  S1 = 1
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_0001046F end
  ::BB_00010449:: -- block 45, succs=[47, 46]
  S0 = a3
  S1 = nil
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_0001045A end
  ::BB_00010452:: -- block 46, succs=[47]
  S0 = 450
  S1 = 100
  S0 = (S0 + S1)
  a3 = S0
  ::BB_0001045A:: -- block 47, succs=[51]
  S0 = a2
  S1 = a3
  S2 = nil
  S3 = nil
  S4 = nil
  S5 = nil
  S6 = nil
  S7 = nil
  S8 = nil
  __ret = f_00055D3D(S0, S1, S2, S3, S4, S5, S6, S7, S8)
  goto BB_00010490
  ::BB_0001046F:: -- block 48, succs=[50, 49]
  S0 = a3
  S1 = nil
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_00010480 end
  ::BB_00010478:: -- block 49, succs=[50]
  S0 = 575
  S1 = 100
  S0 = (S0 + S1)
  a3 = S0
  ::BB_00010480:: -- block 50, succs=[51]
  S0 = a2
  S1 = a3
  S2 = nil
  S3 = nil
  S4 = nil
  S5 = nil
  S6 = nil
  S7 = nil
  S8 = nil
  __ret = f_00055D3D(S0, S1, S2, S3, S4, S5, S6, S7, S8)
  ::BB_00010490:: -- block 51, succs=[53]
  goto BB_000104A5
  ::BB_00010495:: -- block 52, succs=[53]
  S0 = a2
  S1 = 1
  S2 = nil
  S3 = nil
  S4 = nil
  S5 = nil
  S6 = nil
  S7 = nil
  S8 = nil
  __ret = f_00055D3D(S0, S1, S2, S3, S4, S5, S6, S7, S8)
  ::BB_000104A5:: -- block 53, succs=[]
  S0 = nil
  G[15] = S0
  return
  ::BB_000104AA:: -- block 54, succs=[]
  return
end
