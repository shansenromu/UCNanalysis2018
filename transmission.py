import ROOT
import sys
import numpy
import math
import UCN


def ReadCycles(infile, experiments):
  countperiod = 1
  monitorperiod = 0
  backgroundperiod = 10
  binspersec = 5

  for ex in experiments:
    ex['start'] = []
    ex['cyclenumber'] = []
    ex['beamcurrent'] = []
    ex['li6counts'] = []
    ex['countduration'] = []
    ex['monitorcounts'] = []
    ex['monitorduration'] = []
    ex['li6counts2'] = []
    ex['countduration2'] = []
    ex['monitorcounts2'] = []
    ex['monitorduration2'] = []
    ex['li6background'] = []
    ex['he3background'] = []
    ex['li6irradiation'] = []
    ex['he3irradiation'] = []
    ex['irradiationduration'] = []
    ex['backgroundduration'] = []
    ex['beamcurrent'] = []
    ex['mintemperature'] = []
    ex['maxtemperature'] = []
    ex['minvaporpressure'] = []
    ex['maxvaporpressure'] = []
    ex['SCMcurrent'] = []

    ex['Li6rate'] = []
    ex['He3rate'] = []
    ex['li6window'] = []

    ex['productionrate'] = []
    ex['productionrateerr'] = []

    tcn = 'TCN{0}'.format(ex['TCN'])
    ex['channels'] = ROOT.TH1D(tcn + '_ch', tcn + ';Channel;Count', 10, 0, 10)
    ex['channels'].SetDirectory(0)

  for cycle in infile.cycledata:
    run = cycle.runnumber
  
    if not any(run in ex['runs'] for ex in experiments): # if there is no experiment using this cycle
      continue
    
    Li6 = cycle.countsLi6
    He3 = cycle.countsHe3
    d = cycle.durations
   
    # filter useless runs
    beam = [b for b in cycle.B1V_KSM_PREDCUR]
    if min(beam) < 0.1:
      print('SKIPPING cycle {0} in run {1} because beam current dropped below 0.1uA ({2}uA)'.format(cycle.cyclenumber, cycle.runnumber, min(beam)))
      continue
    if numpy.std(beam) > 0.02:
      print('SKIPPING cycle {0} in run {1} because beam current fluctuated by {2}'.format(cycle.cyclenumber, cycle.runnumber, numpy.std(beam)))
      continue
    if Li6[10] == 0:
      print('SKIPPING cycle {0} in run {1} because not all periods contain Li6 data'.format(cycle.cyclenumber, cycle.runnumber))
      continue
    if max(cycle.UCN_UGD_IV1_STATON) < 1:
      print('SKIPPING cycle {0} in run {1} because IV1 never opened!'.format(cycle.cyclenumber, cycle.runnumber))
      continue
    if (any([1e-7 < ig5 < 1e-2 for ig5 in cycle.UCN_EXP_IG5_RDVAC]) 
        #or 
        #any([1e-7 < ig6 < 1e-2 for ig6 in cycle.UCN_EXP_IG6_RDVAC])
       ):
      print ('SKIPPING cycle {0} in run {1} because IG5 was on!'.format(cycle.cyclenumber, cycle.runnumber))
      continue
    if Li6[countperiod] < 10*d[countperiod]:
      print('SKIPPING cycle {0} in run {1} because Li6 seems to see only background ({2}/s)'.format(cycle.cyclenumber, cycle.runnumber, Li6[countperiod]/d[countperiod]))
      continue
    if Li6[backgroundperiod] > 10*d[backgroundperiod]:
      print('SKIPPING cycle {0} in run {1} because Li6 sees high background ({2}/s)'.format(cycle.cyclenumber, cycle.runnumber, Li6[backgroundperiod]/d[backgroundperiod]))
      continue
    if He3[countperiod] < 300:
      print('SKIPPING cycle {0} in run{1} because there are not enough monitor counts ({2} + {3})'.format(cycle.cyclenumber, cycle.runnumber, He3[monitorperiod], He3[countperiod]))
      continue

    if cycle.valve0state[0] != 1 or cycle.valve0state[1] != 1 or cycle.valve1state[0] != 0 or cycle.valve1state[1] != 1:
      print('Abnormal valve configuration in cycle {0} of run {1}'.format(cycle.cyclenumber, cycle.runnumber))

    for ex in experiments:
      if run not in ex['runs']:
        continue

      ex['start'].append(cycle.start)
      ex['cyclenumber'].append(float(cycle.cyclenumber))
      ex['beamcurrent'].append(beam)
      ex['mintemperature'].append(min([min(getattr(cycle,'UCN_ISO_{0}_RDTEMP'.format(TS))) for TS in ['TS11', 'TS12', 'TS14']]))
      ex['maxtemperature'].append(max([max(getattr(cycle,'UCN_ISO_{0}_RDTEMP'.format(TS))) for TS in ['TS11', 'TS12', 'TS14']]))
      if max(cycle.UCN_ISO_PG9L_RDPRESS) >= 2.:
        ex['minvaporpressure'].append(min(cycle.UCN_ISO_PG9H_RDPRESS))
        ex['maxvaporpressure'].append(max(cycle.UCN_ISO_PG9H_RDPRESS))
      else:
        ex['minvaporpressure'].append(min(cycle.UCN_ISO_PG9L_RDPRESS))
        ex['maxvaporpressure'].append(max(cycle.UCN_ISO_PG9L_RDPRESS))
      ex['SCMcurrent'].append([v/250e-6 for v in cycle.SCMVoltages3])

      duration = int(math.floor(cycle.beamonduration + cycle.beamoffduration))
      for det in ['Li6', 'He3']:
        rate = ROOT.TH1D('{0}_{1}_{2}_{3}'.format(tcn, cycle.runnumber, cycle.cyclenumber, det), det + ' rate', duration*20 if det == 'Li6' else duration, 0., duration)
        rate.GetXaxis().SetTitle('Time in cycle (s)')
        rate.GetYaxis().SetTitle('Rate in {0} detector'.format(det))
        for t in getattr(cycle, det + '/hits'):
          rate.Fill(t)
        rate.Sumw2()
        ex[det + 'rate'].append(rate)
        ex[det + 'rate'][-1].SetDirectory(0)

      ex['li6counts'].append(Li6[countperiod])
      ex['countduration'].append(d[countperiod])
      ex['monitorcounts'].append(He3[countperiod])
      ex['monitorduration'].append(d[countperiod])
      triggertime = ex['Li6rate'][-1].GetBinLowEdge(ex['Li6rate'][-1].FindFirstBinAbove(10)) - 60.
      ex['li6window'].append((triggertime, triggertime + 10.))
      ex['li6counts2'].append(len([t for t in getattr(cycle, 'Li6/hits') if d[monitorperiod] + ex['li6window'][-1][0] < t < d[monitorperiod] + ex['li6window'][-1][1]]))
      ex['countduration2'].append(ex['li6window'][-1][1] - ex['li6window'][-1][0])
      he3window = (-10., 0.)
      ex['monitorcounts2'].append(len([t for t in getattr(cycle, 'He3/hits') if d[monitorperiod] + he3window[0] < t < d[monitorperiod] + he3window[1]]))
      ex['monitorduration2'].append(he3window[1] - he3window[0])
      ex['li6background'].append(Li6[backgroundperiod])
      ex['backgroundduration'].append(d[backgroundperiod])
      ex['li6irradiation'].append(Li6[0])
      ex['irradiationduration'].append(d[0])

      for c in getattr(cycle, 'Li6/channel'):
        ex['channels'].Fill(c)

  print('Read {0} cycles\n'.format(len(numpy.concatenate([ex['start'] for ex in experiments]))))

	  
def Transmission(ex):
  print('\nAnalyzing TCN{0}'.format(ex['TCN']))

  if len(ex['start']) == 0:
    print('Found no cycles with run numbers {0}!'.format(ex['runs']))
    return

  ex['li6backgroundrate'], ex['li6backgroundrateerr'] = UCN.BackgroundRate(ex['li6background'], ex['backgroundduration'])
  ex['li6irradiationrate'], ex['li6irradiationrateerr'] = UCN.SubtractBackgroundAndNormalizeRate(ex['li6irradiation'], ex['irradiationduration'], 'li6', \
                                                                                                 [numpy.mean(cur) for cur in ex['beamcurrent']], [numpy.std(cur) for cur in ex['beamcurrent']])
  print('Li6 background rate: {0} +/- {1} 1/s'.format(ex['li6backgroundrate'], ex['li6backgroundrateerr']))

  # report average monitor counts
  monitoravg = numpy.average(ex['monitorcounts'], None, [1./m for m in ex['monitorcounts']], True)
  print('Monitor counts: {0} +/- {1}'.format(monitoravg[0], 1./math.sqrt(monitoravg[1])))

  # report range of beam current
  print('Beam current from {0} to {1} uA'.format(min(min(c) for c in ex['beamcurrent']), max(max(c) for c in ex['beamcurrent'])))

  # report He-II temperature range
  print('Temperatures from {0} to {1} K'.format(min(ex['mintemperature']), max(ex['maxtemperature'])))
  
  canvas = ROOT.TCanvas('c', 'c')
  pdf = 'TCN{0}.pdf'.format(ex['TCN'])

  # plot ratio of background-corrected counts to monitor counts during counting
  y, yerr = UCN.SubtractBackgroundAndNormalize(ex['li6counts'], ex['countduration'], 'li6', ex['monitorcounts'], [math.sqrt(c) for c in ex['monitorcounts']])
  graph = ROOT.TGraphErrors(len(y), numpy.array(ex['cyclenumber']), numpy.array(y), numpy.array([0. for _ in ex['cyclenumber']]), numpy.array(yerr))
  graph.SetTitle('TCN{0}, normalized during counting'.format(ex['TCN']))
  graph.GetXaxis().SetTitle('Cycle')
  graph.GetXaxis().SetLimits(0., max(ex['cyclenumber']))
  graph.GetYaxis().SetTitle('UCN-count-to-monitor ratio')
  graph.SetMarkerStyle(20)
  transfit = ROOT.TF1('transfit', 'pol0', 0, 100)
  transfit.SetParName(0, '#bar{R}_{c}')
  f = graph.Fit(transfit, 'QS')
  graph.Draw('AP')
  canvas.Print(pdf + '(')

  ex['transmission'] = f.GetParams()[0]
  ex['transmissionerr'] = f.GetErrors()[0]*max(f.Chi2()/f.Ndf(), 1.)
  print('Li6-to-He3 ratio during counting: {0} +/- {1}'.format(ex['transmission'], ex['transmissionerr']))

  if min(ex['monitorcounts2']) > 0:
    # plot ratio of background-corrected counts to monitor counts during irradiation
    y, yerr = UCN.SubtractBackgroundAndNormalize(ex['li6counts2'], ex['countduration2'], 'li6', ex['monitorcounts2'], [math.sqrt(c) for c in ex['monitorcounts2']])
    graph = ROOT.TGraphErrors(len(y), numpy.array(ex['cyclenumber']), numpy.array(y), numpy.array([0. for _ in ex['cyclenumber']]), numpy.array(yerr))
    graph.SetTitle('TCN{0}, normalized during irradiation'.format(ex['TCN']))
    graph.GetXaxis().SetTitle('Cycle')
    graph.GetXaxis().SetLimits(0., max(ex['cyclenumber']))
    graph.GetYaxis().SetTitle('UCN-count-to-monitor ratio')
    graph.SetMarkerStyle(20)
    transfit.SetParName(0, '#bar{R}_{i}')
    f = graph.Fit(transfit, 'QS')
    graph.Draw('AP')
    canvas.Print(pdf)

    ex['transmission2'] = f.GetParams()[0]
    ex['transmission2err'] = f.GetErrors()[0]*max(f.Chi2()/f.Ndf(), 1.)
    print('Li6-to-He3 ratio during irradiation: {0} +/- {1}\n'.format(ex['transmission2'], ex['transmission2err']))

  UCN.PrintTemperatureVsCycle(ex, pdf)
  
  he3axis = ex['He3rate'][0].GetXaxis()
  he3rate = ROOT.TH1D('TCN{0}_He3'.format(ex['TCN']), ';Time (s); He3 rate (1/s)', he3axis.GetNbins(), he3axis.GetXmin(), he3axis.GetXmax())
  he3rate.SetDirectory(0)
  for he3 in ex['He3rate']:
    he3rate.Add(he3)
  satfit = ROOT.TF1('satfit', '[0]*(erfc(sqrt([1]/x)-sqrt(x/[2]))-exp(4*sqrt([1]/[2]))*erfc(sqrt([1]/x)+sqrt(x/[2])))', 0, 60)
  for i, p in enumerate(zip([500., 12., 30.], [10000., 100., 100.], ['p_{0}', '#tau_{d}', '#tau'])):
    satfit.SetParameter(i, p[0])
    satfit.SetParName(i, p[2])
  fit = he3rate.Fit(satfit, 'MRSQ')
  he3rate.Draw()
  canvas.Print(pdf)

  li6fit = ROOT.TF1('li6fit', '(x<60 + [0]?0:[1])*(1 - exp(-(x - 60 - [0])/[2]))*(exp(-(x - 60 - [0])/[3]) + [4]*exp(-(x - 60 - [0])/[5]) +[6]*exp(-(x - 60 - [0])/[7])) + [8]', 60, 180)
  li6axis = ex['Li6rate'][0].GetXaxis()
  binwidth = li6axis.GetBinWidth(1)
  li6rate = ROOT.TH1D('TCN{0}_Li6'.format(ex['TCN']), ';Time (s); Li6 rate (1/{0}s)'.format(binwidth), li6axis.GetNbins(), li6axis.GetXmin(), li6axis.GetXmax())
  li6rate.SetDirectory(0)
  for h in ex['Li6rate']:
    li6rate.Add(h)
  li6fit.SetNpx(li6rate.GetNbinsX())
  li6fit.SetParameters(1.5, 1000., 0.2, 1.5, 1., 14., 0.1, 30.)
  for i, p in enumerate(zip([5, 1e5, 5., 10., 10, 30., 10., 100.], ['t_{d}', 'p_{0}', '#tau_{rise}', '#tau_{1}', 'N_{2}', '#tau_{2}', 'N_{3}', '#tau_{3}'])):
    li6fit.SetParLimits(i, 0., p[0])
    li6fit.SetParName(i, p[1])
  li6fit.FixParameter(8, UCN.DetectorBackground['li6'][0]*binwidth)
  li6fit.SetParError(8, UCN.DetectorBackground['li6'][1]*binwidth)
  li6rate.Fit(li6fit, 'MRSQL', '')
#  canvas.SetLogy()
  li6rate.Draw()
  canvas.Print(pdf)
#  canvas.SetLogy(0)

  li6background = ROOT.TH1D('Li6background', ';Time (s); Li6 background rate (1/{0}s)'.format(binwidth), li6axis.GetNbins(), li6axis.GetXmin(), li6axis.GetXmax())
  li6background.SetDirectory(0)
  for b in range(li6background.GetNbinsX()):
    li6background.SetBinContent(b, UCN.DetectorBackground['li6'][0]*li6background.GetBinWidth(b))
    li6background.SetBinError(b, UCN.DetectorBackground['li6'][1]*li6background.GetBinWidth(b))
  li6background.Sumw2()

  li6norm = ROOT.TH1D('TCN{0}_Li6_norm'.format(ex['TCN']), ';Time (s);Li6 rate normalized during counting (1/{0}s)'.format(binwidth), int(li6axis.GetNbins()/4.), li6axis.GetXmin(), li6axis.GetXmax())
  li6norm.SetDirectory(0)
  for li6, m in zip(ex['Li6rate'], ex['monitorcounts']):
    li6copy = li6.Clone()
    li6copy.Add(li6background, -1.)
    li6copy.Rebin(4)
    normhist = ROOT.TH1D('normhist', ';Time (s);Normalization factor', int(li6axis.GetNbins()/4.), li6axis.GetXmin(), li6axis.GetXmax())
    for b in range(normhist.GetNbinsX()):
      normhist.SetBinContent(b, m)
      normhist.SetBinError(b, math.sqrt(m))
    normhist.Sumw2()
    li6copy.Divide(normhist)
    li6copy.SetBit(ROOT.TH1.kIsAverage)
    li6norm.Add(li6copy)
    li6norm.SetBit(ROOT.TH1.kIsAverage)
  li6norm.Draw()
  canvas.Print(pdf)
  ex['Li6rate_normalized'] = li6norm

  li6norm2 = ROOT.TH1D('TCN{0}_Li6_norm'.format(ex['TCN']), ';Time (s);Li6 rate normalized during irradiation (1/{0}s)'.format(binwidth), int(li6axis.GetNbins()/4.), li6axis.GetXmin(), li6axis.GetXmax())
  li6norm2.SetDirectory(0)
  for li6, m in zip(ex['Li6rate'], ex['monitorcounts2']):
    li6copy = li6.Clone()
    li6copy.Add(li6background, -1.)
    li6copy.Rebin(4)
    normhist2 = ROOT.TH1D('normhist', ';Time (s);Normalization factor', int(li6axis.GetNbins()/4.), li6axis.GetXmin(), li6axis.GetXmax())
    for b in range(normhist2.GetNbinsX()):
      normhist2.SetBinContent(b, m)
      normhist2.SetBinError(b, math.sqrt(m))
    normhist2.Sumw2()
    li6copy.Divide(normhist2)
    li6copy.SetBit(ROOT.TH1.kIsAverage)
    li6norm2.Add(li6copy)
    li6norm2.SetBit(ROOT.TH1.kIsAverage)
  li6norm2.Draw()
  canvas.Print(pdf)
  ex['Li6rate_normalized2'] = li6norm2

  li6rate.SetStats(False)
  li6rate.GetYaxis().SetTitle('Ratio of cumulated rates')
  li6rate.Add(li6background, -len(ex['Li6rate']))
  li6rate.Rebin(int(1./binwidth))
  li6rate.Divide(he3rate)
  li6rate.Draw('HIST')
  canvas.Print(pdf)
  
  rateratio = ROOT.TH1D('TCN{0}_ratio'.format(ex['TCN']), ';Time (s);Average rate ratio', int(he3axis.GetNbins()/10.), he3axis.GetXmin(), he3axis.GetXmax())
  rateratio.SetDirectory(0)
  for li6, he3 in zip(ex['Li6rate'], ex['He3rate']):
    li6.Add(li6background, -1)
    li6.Rebin(int(10./binwidth))
    he3.Rebin(10)
    li6.Divide(he3)
#    li6.Draw()
#    canvas.Print(pdf)
    li6.SetBit(ROOT.TH1.kIsAverage)
    rateratio.Add(li6)
    rateratio.SetBit(ROOT.TH1.kIsAverage)
  rateratio.Draw()
  canvas.Print(pdf)
  
  ex['channels'].Draw()
  canvas.Print(pdf)

  window = ROOT.TH1I('li6window','Li6 window;Time after valve opened (s);Frequency',100,0.,5.)
  for w in ex['li6window']:
    window.Fill(w[0])
  window.Draw()
  canvas.Print(pdf + ')')



# normalize one time-of-flight spectrum to another and print to pdf
def Normalize(experiments, transtcn, reftcn):
  trans = next((ex for ex in experiments if ex['TCN'].startswith(transtcn)), None) # find experiment with given TCN number
  ref = next((ex for ex in experiments if ex['TCN'].startswith(reftcn)), None) # find reference experiment with given TCN number
  if not trans or not ref:
    return 0., 0.


  transmission = trans['transmission']/ref['transmission']
  transmissionerr = math.sqrt((trans['transmissionerr']/trans['transmission'])**2 + (ref['transmissionerr']/ref['transmission'])**2)*transmission
  print('Transmission ratio {1}/{2} (normalized during counting): {0} +/- {3}'.format(transmission, trans['TCN'], ref['TCN'], transmissionerr))

  transmission2 = trans['transmission2']/ref['transmission2']
  transmission2err = math.sqrt((trans['transmission2err']/trans['transmission2'])**2 + (ref['transmission2err']/ref['transmission2'])**2)*transmission
  print('Transmission ratio {1}/{2} (normalized during irradiation): {0} +/- {3}'.format(transmission2, trans['TCN'], ref['TCN'], transmission2err))


  tofspec = trans['Li6rate_normalized'].Clone() # make copy of tof spectrum
  tofspec.Divide(ref['Li6rate_normalized']) # normalize to reference spectrum
  tofspec.GetXaxis().SetRangeUser(60, 120)
  tofspec.GetYaxis().SetRangeUser(0, 1.5)
  tofspec.SetTitle('TCN{0} normalized to TCN{1}: {2} +/- {3}'.format(transtcn, reftcn, transmission, transmissionerr))
  tofspec.GetYaxis().SetTitle('Transmission (normalized during counting)')
  c = ROOT.TCanvas('c', 'c')
  tofspec.Draw()
  pdf = 'TCN{0}_TCN{1}.pdf'.format(transtcn, reftcn)
  c.Print(pdf + '(') # print to pdf

  tofspec2 = trans['Li6rate_normalized2'].Clone() # make copy of tof spectrum
  tofspec2.Divide(ref['Li6rate_normalized2']) # normalize to reference spectrum
  tofspec2.GetXaxis().SetRangeUser(60, 120)
  tofspec2.GetYaxis().SetRangeUser(0, 1.5)
  tofspec2.SetTitle('TCN{0} normalized to TCN{1}: {2} +/- {3}'.format(transtcn, reftcn, transmission2, transmission2err))
  tofspec2.GetYaxis().SetTitle('Transmission (normalized during irradiation)')
  tofspec2.Draw()
  c.Print(pdf + ')') # print to pdf

  return transmission, transmissionerr, transmission2, transmission2err


### Main program starts here ###

ROOT.gStyle.SetOptStat(1001111)
ROOT.gStyle.SetOptFit(1111)
ROOT.gROOT.SetBatch(1)
ROOT.gErrorIgnoreLevel = ROOT.kWarning + 1
ROOT.Math.IntegratorOneDimOptions.SetDefaultIntegrator('GaussLegendre')

# list of runs belonging to each experiment
experiments = [{'TCN': '18-028 (IV2+UGD17, no elbow), production up to IV1', 'runs': [ 929]},
               {'TCN': '18-029 (IV2+UGD17, no elbow)', 'runs': [ 930, 934]},
               {'TCN': '18-030 (IV2+UGD17+elbow), production up to IV1', 'runs': [ 937]},
               {'TCN': '18-031 (IV2+UGD17+elbow)', 'runs': [ 938]},
               {'TCN': '18-035 (IV2+UGD22+IV3, O-rings out)', 'runs': [ 944]},
               {'TCN': '18-043 (IV2+UGD22+IV3, O-rings out, IV2 open during production)', 'runs': [ 954]},
               {'TCN': '18-045 (IV2+UGD22+IV3, O-rings in)', 'runs': [ 964]},
               {'TCN': '18-080 (UGD22+2, IV1 closed after production)', 'runs': [ 973]},
               {'TCN': '18-053 (burst disk+UGD2)', 'runs': [ 985]},
               {'TCN': '18-285 (UGD22+19, MV open)', 'runs': [ 990]},
               {'TCN': '18-085 (UGD22+19)', 'runs': [ 993]},
               {'TCN': '18-090 (UGD22+UGA11+UGG3+UGA5)', 'runs': [1000]},
               {'TCN': '18-290 (UGD22+UGA5+UGG3+UGA6)', 'runs': [1009]},
               {'TCN': '18-060 (UGD10+17+11)', 'runs': [1013]},
			   
               {'TCN': '18-065_0A', 'runs': [1054]},
               {'TCN': '18-065_25A', 'runs': [1055]},
               {'TCN': '18-065_200A', 'runs': [1056]},
               {'TCN': '18-065_100A', 'runs': [1057]},
               {'TCN': '18-065_150A', 'runs': [1058]},
               {'TCN': '18-065_175A', 'runs': [1059]},
               {'TCN': '18-065_125A', 'runs': [1064]},
               {'TCN': '18-065_75A', 'runs': [1065]},
               {'TCN': '18-065_50A', 'runs': [1066]},
			   
               {'TCN': '18-265_0A', 'runs': [1081]},
               {'TCN': '18-265_200A', 'runs': [1082]},
               {'TCN': '18-265_100A', 'runs': [1083]},
               {'TCN': '18-265_150A', 'runs': [1084]},
               {'TCN': '18-265_50A', 'runs': [1085]},
               {'TCN': '18-265_75A', 'runs': [1086]},
               {'TCN': '18-265_25A', 'runs': [1087]},
			   
               {'TCN': '18-115 (UGD22+2+Ti)', 'runs': [1125]},
               {'TCN': '18-245 (IV2+UGD22+IV3, O-rings in)', 'runs': [1129]},
               {'TCN': '18-480 (UGD22+2)', 'runs': [1131]},
               {'TCN': '18-480 (UGD22+2, IV1 closed after production)', 'runs': [1132, 1133]},
               {'TCN': '18-057 (spider+UGD2)', 'runs': [1141]},
               {'TCN': '18-302 (high position: IV2+elbow+UGD10+18)', 'runs': [1165]},
               {'TCN': '18-240 (high position: IV2+elbow+UGD10+Al+UGD18)', 'runs': [1176]},
               {'TCN': '18-215 (high position: UGD22+20+Ti)', 'runs': [1181]},
               {'TCN': '18-380 (high position: UGD22+20)', 'runs': [1188]},
               {'TCN': '18-310 (high position: UGD22+20, smooth elbow)', 'runs': [1192]}]

ReadCycles(ROOT.TFile(sys.argv[1]), experiments)

# loop over experiments and analyze transmission in runs
for ex in experiments:
  Transmission(ex)

UCN.PrintBackground(experiments, 'li6')
UCN.PrintMonitorCounts(experiments)

Normalize(experiments, '18-215', '18-380') # Ti foil in high position
Normalize(experiments, '18-115', '18-480') # Ti foil in low position
Normalize(experiments, '18-240', '18-302') # Al foil above detector
Normalize(experiments, '18-310', '18-380') # smooth elbow
Normalize(experiments, '18-035', '18-031') # UGD22+IV3 compared to UGD17 only
Normalize(experiments, '18-045', '18-035') # UGD22+IV3 compared to UGD17 only
Normalize(experiments, '18-057', '18-045') # spider + UGD2 compared to UGD22
Normalize(experiments, '18-053', '18-045') # burst disk + UGD2 compared to UGD22
Normalize(experiments, '18-053', '18-480') # burst disk compared to UGD22
Normalize(experiments, '18-057', '18-053') # spider compared to burst disk
Normalize(experiments, '18-480', '18-045') # Stainless guide compared to no guide
Normalize(experiments, '18-480', '18-245') # Stainless guide compared to no guide
Normalize(experiments, '18-085', '18-045') # NiP-coated guide compared to no guide
Normalize(experiments, '18-085', '18-245') # NiP-coated guide compared to no guide
Normalize(experiments, '18-090', '18-045') # NiMo-coated glass guide compared to no guide
Normalize(experiments, '18-090', '18-245') # NiMo-coated glass guide compared to no guide
Normalize(experiments, '18-290', '18-045') # NiMo-coated glass guide compared to no guide
Normalize(experiments, '18-290', '18-245') # NiMo-coated glass guide compared to no guide
Normalize(experiments, '18-045', '18-245') # Compare reference experiments
Normalize(experiments, '18-085', '18-480') # NiP-coated guide compared to stainless guide
Normalize(experiments, '18-090', '18-480') # NiMo-coated glass guide compared to stainless guide
Normalize(experiments, '18-290', '18-480') # NiMo-coated glass guide compared to stainless guide
Normalize(experiments, '18-060', '18-045') # UGD10+17+11 compared to no guide
Normalize(experiments, '18-065_0A', '18-045') # warm bore without foil
Normalize(experiments, '18-065_0A', '18-060') # warm bore without foil
Normalize(experiments, '18-265_0A', '18-045') # warm bore with foil
Normalize(experiments, '18-265_0A', '18-060') # warm bore with foil
Normalize(experiments, '18-265_0A', '18-065') # warm bore with foil
Normalize(experiments, '18-029', '18-031') # compare no elbow with elbow

canvas = ROOT.TCanvas('c','c')

for tcn in ['18-065', '18-265']: # normalize all the SCM measurements to zero current and plot transmission vs. SCMcurrent
  gr = ROOT.TGraphErrors()
  gr2 = ROOT.TGraphErrors()
  for cur in ['0', '25', '50', '75', '100', '125', '150', '175', '200']:
    fulltcn = '{0}_{1}A'.format(tcn, cur)
    ex = next((ex for ex in experiments if ex['TCN'].startswith(fulltcn)), None)
    if not ex:
      continue
    t, te, t2, t2e = Normalize(experiments, fulltcn, tcn+'_0A')
    SCMcurrent = numpy.concatenate(ex['SCMcurrent'])
    i = gr.GetN()
    gr.SetPoint(i, numpy.mean(SCMcurrent), t)
    gr.SetPointError(i, numpy.std(SCMcurrent)/math.sqrt(len(SCMcurrent)), te)
    gr2.SetPoint(i, numpy.mean(SCMcurrent), t2)
    gr2.SetPointError(i, numpy.std(SCMcurrent)/math.sqrt(len(SCMcurrent)), t2e)
  gr.SetTitle('TCN' + tcn)
  gr.GetXaxis().SetTitle('SCM current (A)')
  gr.GetYaxis().SetTitle('Transmission')
  canvas = ROOT.TCanvas('c','c')
  gr.Draw('AP')
  gr2.SetLineColor(ROOT.kRed)
  gr2.SetMarkerColor(ROOT.kRed)
  gr2.Draw('SAMEP')
  canvas.Print('TCN{0}.pdf'.format(tcn))

