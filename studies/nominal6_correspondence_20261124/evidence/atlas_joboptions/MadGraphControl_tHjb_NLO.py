from MadGraphControl.MadGraphUtils import *

# General settings
nevents=5500
gridpack_dir='madevent/'
gridpack_mode=False
cluster_type='lsf'
cluster_queue='1nd'
mode=2
njobs=132
runName='run_01'

tHjb_4fl = [ 346188, 346414, 346229, 346230, 346231, 346232, 346233, 346234, 346602, 346707, 346708, 346709, 346710, 346711, 346712, 346713, 346714 ]
tHjb_4fl_mass = [ 346707, 346708, 346709, 346710, 346711, 346712, 346713, 346714 ]
tHjb_4fl_HW7 = [346602]
tHjb_5fl = [ 346221, 346415 ]
# these DSIDs have modified param cards (BSM couplings)
tHjb_4fl_yt_minus1 = [ 346231, 346232 ] # top yukawa -1*SM value
tHjb_4fl_yt_plus2 = [ 346233, 346234 ] # top yukawa +2*SM value
# list of all DSIDs with modified param cards (used in the generate call)
tHjb_4fl_modparam = tHjb_4fl_yt_minus1+tHjb_4fl_yt_plus2+tHjb_4fl_mass
massdict= {
    346707 : 110,
    346708 : 122,
    346709 : 123,
    346710 : 124,
    346711 : 126,
    346712 : 127,
    346713 : 130,
    346714 : 140,
}


if runArgs.runNumber in tHjb_4fl:
    
    mgproc="generate p p > h t1 b1 j $$ w+ w- [QCD]"
    name='tHjb_4fl'
    process="pp>tHbj"
    topdecay='''decay t > w+ b, w+ > all all
    decay t~ > w- b~, w- > all all'''
    gridpack_mode=True
    gridpack_dir='madevent/'
    parton_shower='PYTHIA8'

    if runArgs.runNumber in tHjb_4fl_mass: #I do not like to create the grid
        mh = massdict.get(runArgs.runNumber, 125.0)
        name='tHjb'+str(mh)+'_4fl'
        masses = {'25':str(mh)+'  #  MH'}
        print 'Higgs mass will be set to ', mh
    if runArgs.runNumber in tHjb_4fl_HW7:
        parton_shower='HERWIGPP'
        gridpack_mode=False
        gridpack_dir='madevent/'

    fcard = open('proc_card_mg5.dat','w')
    fcard.write("""
    import model loop_sm
    define p = g u c d s u~ c~ d~ s~
    define j = g u c d s u~ c~ d~ s~
    define t1 = t t~
    define b1 = b b~
    """+mgproc+"""
    output -f
    """)
    fcard.close()

    extras = {'pdlabel'        : "'lhapdf'",
              'lhaid'          : 260400,
              'parton_shower'  : parton_shower,
              'reweight_scale' : 'True',
              'reweight_PDF'   : 'True',
              'PDF_set_min'    : 260401,
              'PDF_set_max'    : 260500,
              'bwcutoff'       : 50.,
              'dynamical_scale_choice' : 3 }

elif runArgs.runNumber in tHjb_5fl:
    
    mgproc="generate p p > h t j $$ w+ w- [QCD]"
    mgprocadd="add process p p > h t~ j $$ w+ w- [QCD]"
    name='tHjb_5fl'
    process="pp>tHj"
    topdecay='''decay t > w+ b, w+ > all all
    decay t~ > w- b~, w- > all all'''
    gridpack_mode=True
    gridpack_dir='madevent/'

    fcard = open('proc_card_mg5.dat','w')
    fcard.write("""
    import model loop_sm-no_b_mass
    define p = g u c d s b u~ c~ d~ s~ b~
    define j = g u c d s b u~ c~ d~ s~ b~
    define q = u c d s b t
    define q~ = u~ c~ d~ s~ b~ t~
    """+mgproc+"""
    """+mgprocadd+"""
    output -f
    """)
    fcard.close()
    
    extras = {'pdlabel'        : "'lhapdf'",
              'lhaid'          : 260000,
              'parton_shower'  : parton_shower,
              'reweight_scale' : 'True',
              'reweight_PDF'   : 'True',
              'PDF_set_min'    : 260001,
              'PDF_set_max'    : 260100,
              'bwcutoff'       : 50.,
              'dynamical_scale_choice' : 3 }

else:
    raise RuntimeError("runNumber %i not recognised in these jobOptions."%runArgs.runNumber)

if runArgs.runNumber in tHjb_4fl_yt_minus1:
    name+='_yt_minus1'
elif runArgs.runNumber in tHjb_4fl_yt_plus2:
    name+='_yt_plus2'
    
runName = 'madgraph.'+str(runArgs.runNumber)+'.MadGraph_'+str(name)

beamEnergy=-999
if hasattr(runArgs,'ecmEnergy'):
    beamEnergy = runArgs.ecmEnergy / 2.
else:
    raise RuntimeError("No center of mass energy found.")

process_dir = new_process(grid_pack=gridpack_dir)

build_run_card(run_card_old=get_default_runcard(proc_dir=process_dir),run_card_new='run_card.dat',
               nevts=nevents,rand_seed=runArgs.randomSeed,beamEnergy=beamEnergy,xqcut=0.,
               extras=extras)

if runArgs.runNumber in tHjb_4fl_mass:
    build_param_card(param_card_old=process_dir+'/Cards/param_card.dat',param_card_new='param_card_mass.dat', masses=masses)

madspin_dir = 'my_madspin'
madspin_card_loc='madspin_card.dat'

if not hasattr(runArgs, 'inputGenConfFile'):
    fMadSpinCard = open('madspin_card.dat','w')
    fMadSpinCard.write('import Events/'+runName+'/events.lhe.gz\n')
    #fMadSpinCard.write('set ms_dir MadSpin\n')
    fMadSpinCard.write('set ms_dir '+madspin_dir+'\n')
else:
    os.unlink(gridpack_dir+'Cards/madspin_card.dat')
    fMadSpinCard = open(gridpack_dir+'Cards/madspin_card.dat','w')
    fMadSpinCard.write('import '+gridpack_dir+'Events/'+runName+'/events.lhe.gz\n')
    fMadSpinCard.write('set ms_dir '+gridpack_dir+'MadSpin\n')
    fMadSpinCard.write('set ms_dir '+madspin_dir+'\n')
    fMadSpinCard.write('set seed '+str(10000000+int(runArgs.randomSeed))+'\n')
fMadSpinCard.write('''set Nevents_for_max_weigth 2000 # number of events for the estimate of the max. weight (default: 75)
set max_weight_ps_point 500  # number of PS to estimate the maximum for each event (default: 400)
'''+topdecay+'''
launch''')
fMadSpinCard.close()

## the generate call differs for the cases of using a nominal(SM) or modified(BSM) param card
# run with nominal param card
if runArgs.runNumber not in tHjb_4fl_modparam:   
    generate(run_card_loc='run_card.dat',param_card_loc=None,mode=mode,njobs=njobs,proc_dir=process_dir,run_name=runName,madspin_card_loc=madspin_card_loc,
             grid_pack=gridpack_mode,gridpack_dir=gridpack_dir,nevents=nevents,random_seed=runArgs.randomSeed,required_accuracy=0.001)
# run with modified param card
else:
    mod_paramcard_name = ''
    if runArgs.runNumber in tHjb_4fl_yt_minus1:
        mod_paramcard_name = 'param_card_yt_minus1.dat'
    elif runArgs.runNumber in tHjb_4fl_yt_plus2:
        mod_paramcard_name = 'param_card_yt_plus2.dat'
    elif runArgs.runNumber in tHjb_4fl_mass:
        mod_paramcard_name = 'param_card_mass.dat'
    else:
        raise RuntimeError("No modified param card instuction found for %i ."%runArgs.runNumber)

    mod_paramcard = subprocess.Popen(['get_files','-data',mod_paramcard_name]).communicate()
    if not os.access(mod_paramcard_name, os.R_OK):
        print 'ERROR: Could not get param card'
        raise RuntimeError("parameter card '%s' missing!"%mod_paramcard_name)

    generate(run_card_loc='run_card.dat',param_card_loc=mod_paramcard_name,mode=mode,njobs=njobs,proc_dir=process_dir,run_name=runName,madspin_card_loc=madspin_card_loc,
             grid_pack=gridpack_mode,gridpack_dir=gridpack_dir,nevents=nevents,random_seed=runArgs.randomSeed,required_accuracy=0.001,cluster_type=cluster_type,cluster_queue=cluster_queue)    

### common to all jobs
outputDS=arrange_output(run_name=runName,proc_dir=process_dir,lhe_version=3,saveProcDir=True)

if 'ATHENA_PROC_NUMBER' in os.environ:
    print 'Noticed that you have run with an athena MP-like whole-node setup.  Will re-configure now to make sure that the remainder of the job runs serially.'
    njobs = os.environ.pop('ATHENA_PROC_NUMBER')
    # Try to modify the opts underfoot
    if not hasattr(opts,'nprocs'): print 'Did not see option!'
    else: opts.nprocs = 0
    print opts

# --------------------------------------------------------------
# Run Pythia8 or Herwig7 Showering
# --------------------------------------------------------------

if not runArgs.runNumber in tHjb_4fl_HW7:
    runArgs.inputGeneratorFile=outputDS    
    evgenConfig.description = 'aMcAtNlo tHjb'
    evgenConfig.keywords+=['Higgs', 'tHiggs']
    evgenConfig.inputfilecheck = outputDS
    evgenConfig.contact = ['liza.mijovic@cern.ch', 'a.hasib@cern.ch' ]
    include("MC15JobOptions/Pythia8_A14_NNPDF23LO_EvtGen_Common.py")
    include("MC15JobOptions/Pythia8_aMcAtNlo.py")
    include("MC15JobOptions/Pythia8_SMHiggs125_inc.py")
elif runArgs.runNumber in tHjb_4fl_HW7:
    runArgs.inputGeneratorFile=outputDS
    evgenConfig.generators += ["aMcAtNlo", "Herwig7"]
    evgenConfig.description = 'MG5_aMC@NLO+Herwig7+EvtGen '+name+' OTF, H7p1 default tune, ME NNPDF 3.0 NLO'
    evgenConfig.tune = "H7.1-Default"
    evgenConfig.contact = ['maria.moreno.llacer@cern.ch']
    include("MC15JobOptions/Herwig7_LHEF.py")
    Herwig7Config.me_pdf_commands(order="NLO", name="NNPDF30_nlo_as_0118")
    Herwig7Config.tune_commands()
    Herwig7Config.lhef_mg5amc_commands(lhe_filename=runArgs.inputGeneratorFile, me_pdf_order="NLO")
    include("MC15JobOptions/Herwig71_EvtGen.py")
    # only consider H->gamgam decays
    Herwig7Config.add_commands("""
    # force H->gamgam decays
    do /Herwig/Particles/h0:SelectDecayModes h0->gamma,gamma;
    # print out Higgs decays modes and branching ratios to log.generate
    do /Herwig/Particles/h0:PrintDecayModes
    """)
    Herwig7Config.run()
else:
    theApp.finalize()
    theApp.exit()

