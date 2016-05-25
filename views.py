from django.shortcuts import render, render_to_response
from django.http import HttpResponse
from django.db.models import Q, F, Count
import csv

from irndb2.models import Target, T2G, T2K, T2W, T2K, T2C7, Go, Kegg, Wikipath, Msigdb_c7, Mirna, M2T_EXP, M2T_PRED, Lncrna, L2T, Pirna, P2T # use db of irn2 needs changing to .models

# GLOBAL VARIABLE: change according to the url.py of the main project
# e.g. url(r'^apps/irndb/', include('irndb2.urls', namespace="irndb2")),
_APP_LINK_PREFIX = '/apps/irndb'

#----------------------------------------------------------------
# VIEW methods
#----------------------------------------------------------------
def mirna_method(request, name, flush=True):
    context = {}
    context["entity_type"] = "mirna"
    
    ## flush the session store of pirna
    if flush:
        try:
            del request.session['mirnas']
        except:
            request.session['mirnas'] = {}
 
    # Need a store for rnas if not already there
    if 'mirnas' not in request.session:
        request.session['mirnas'] = {}

    a = Mirna.objects.filter(mname__regex=r'^%s$'%name) # exact match, kind of a hack as the __exact did not work
    if len(a)>1:
        context["error"] = 'Query "%s" resulted in more then 1 entitiy.'%name
        return render(request, "irndb2/404.html", context)
    elif len(a)==0:
        context["error"] = 'Query "%s" resulted in 0 entities.'%name
        return render(request, "irndb2/404.html", context)
    else:
        mirna_obj = a[0]
        mid = mirna_obj.id

    context["m"] = mirna_obj

    aImmStrictExp = []
    aImmStrict = []
    aImmExp = []
    aImm = []

    ## check if mirna still in session/cache if so, use existing and return
    if mid in request.session['mirnas']:
        bM = 1
        aImmStrictExp = request.session['mirnas'][mid]['targets_imm_strict_exp']
        aImmStrict = request.session['mirnas'][mid]['targets_imm_strict']
        aImmExp = request.session['mirnas'][mid]['targets_imm_exp']
        aImm = request.session['mirnas'][mid]['targets_imm']
    else:
        bM = 0
        #aTargets_all = set()
        # targets
        mE = M2T_EXP.objects.filter(mirna=mid,target__strict__gt=-1).select_related('target').values_list('target__id', 'target__symbol','target__tname','target__immusources','target__strict','sources').distinct()
        for tRes in mE:
            #aTargets_all.add(tRes[0])
            tRes = list(tRes)
            tRes[3] = tRes[3].split(',')
            tRes[5] = tRes[5].split(',')
            if tRes[4] == 1:
                aImmStrictExp.append(tRes) ## id, symbol, tname, immusources, strict, sources
            else:
                aImmExp.append(tRes)

        mP = M2T_PRED.objects.filter(mirna=mid,target__strict__gt=-1).select_related('target').values_list('target__id', 'target__symbol','target__tname','target__immusources','target__strict','sources').distinct()
        for tRes in mP:
            #aTargets_all.add(tRes[0])
            tRes = list(tRes)
            tRes[3] = tRes[3].split(',')
            tRes[5] = tRes[5].split(',')
            if tRes[4] == 1:
                aImmStrict.append(tRes)
            else:
                aImm.append(tRes)

        ## setup session variable with targets of miRNA
        request.session['mirnas'][mid] = { 'targets_imm_strict':aImmStrict,
                                           'targets_imm':aImm,
                                           'targets_imm_strict_exp':aImmStrictExp,
                                           'targets_imm_exp':aImmExp }
        request.session.modified = True

     ## type of context to return
    sTYPE = request.GET.get('type', 'a')
    if sTYPE not in ['p','g','r','t']:
        context = {'m':mirna_obj}
        return render(request, 'irndb2/mirna_base.html', context)
    
    elif sTYPE=='g':
        ## fetch go from session cache if exists or create new
        if 'go_p_exp' in request.session['mirnas'][mid]:
            aPexp  = request.session['mirnas'][mid]['go_p_exp']
            aPpred = request.session['mirnas'][mid]['go_p']
            aFexp  = request.session['mirnas'][mid]['go_f_exp']
            aFpred = request.session['mirnas'][mid]['go_f']
            sGexisted = '1'
        else:
            ## targets immunological mouse experiemtnal
            sGexisted = '0'
            aTargets = list(set([a[0] for a in aImmStrictExp+aImmExp]))
            aG = T2G.objects.filter(target__in=aTargets).select_related('target', 'go').values_list('go__goid', 'go__goname', 'go__gocat', 'target__id', 'target__symbol', 'target__tname').distinct()
            dGp = {}
            dGf = {}
            for tRes in aG:
                tG = (tRes[0], tRes[1])
                if tRes[2]=='Process':
                    if tG not in dGp:
                        dGp[tG] = set()
                    dGp[tG].add((tRes[4], tRes[3], tRes[5]))
                elif tRes[2]=='Function':
                    if tG not in dGf:
                        dGf[tG] = set()
                    dGf[tG].add((tRes[4], tRes[3], tRes[5]))

            aPexp = []
            for k,v in dGp.items():
                aT = list(v)
                aT.sort()
                aPexp.append({'goid':k[0], 'goname':k[1], 'targets':aT})
            aFexp = []
            for k,v in dGf.items():
                aT = list(v)
                aT.sort()
                aFexp.append({'goid':k[0], 'goname':k[1], 'targets':aT})

            ## predicted mouse
            aTargets = list(set([a[0] for a in aImmStrict+aImm]))
            aG = T2G.objects.filter(target__in=aTargets).select_related('target', 'go').values_list('go__goid', 'go__goname', 'go__gocat', 'target__id', 'target__symbol', 'target__tname').distinct()
            dGp = {}
            dGf = {}
            for tRes in aG:
                tG = (tRes[0], tRes[1])
                if tRes[2]=='Process':
                    if tG not in dGp:
                        dGp[tG] = set()
                    dGp[tG].add((tRes[4], tRes[3], tRes[5]))
                elif tRes[2]=='Function':
                    if tG not in dGf:
                        dGf[tG] = set()
                    dGf[tG].add((tRes[4], tRes[3], tRes[5]))

            aPpred = []
            for k,v in dGp.items():
                aT = list(v)
                aT.sort()
                aPpred.append({'goid':k[0], 'goname':k[1], 'targets':aT})
            aFpred = []
            for k,v in dGf.items():
                aT = list(v)
                aT.sort()
                aFpred.append({'goid':k[0], 'goname':k[1], 'targets':aT})

            ## puch to session cash
            request.session['mirnas'][mid]['go_p_exp'] = aPexp
            request.session['mirnas'][mid]['go_p'] = aPpred
            request.session['mirnas'][mid]['go_f_exp'] = aFexp
            request.session['mirnas'][mid]['go_f'] = aFpred
            request.session.modified = True


        context = {'go_p_exp':aPexp, 'go_p':aPpred, 'go_f_exp':aFexp, 'go_f':aFpred, 'existed':sGexisted}
        return render(request, 'irndb2/mg.html', context)

    elif sTYPE=="p":
        ## fetch pathways from session cache if exists or create new
        if 'wikipath_exp' in request.session['mirnas'][mid]:
            aWexp  = request.session['mirnas'][mid]['wikipath_exp']
            aKexp  = request.session['mirnas'][mid]['kegg_exp']
            aWpred = request.session['mirnas'][mid]['wikipath_pred']
            aKpred = request.session['mirnas'][mid]['kegg_pred']
            sPexisted = '1'
        else:
            ## create new
            sPexisted = '0'
            ## targets immunological mouse+human experiemtnal
            aTargets = list(set([a[0] for a in aImmStrictExp+aImmExp]))
            # wikipath exp
            aW = T2W.objects.filter(target__in=aTargets).select_related('target', 'wikipath').values_list('wikipath__wikipathid', 'wikipath__wikipathname', 'target__id', 'target__symbol', 'target__tname').distinct()
            dW = {}
            for tRes in aW:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aW = []
            for k,v in dW.items():
                aT = list(v)
                aT.sort()
                aW.append({'pathid':k[0], 'pathname':k[1], 'targets':aT})
            aWexp = aW[:]

            aW = T2K.objects.filter(target__in=aTargets).select_related('target', 'kegg').values_list('kegg__keggid', 'kegg__keggname', 'target__id', 'target__symbol', 'target__tname').distinct()
            dW = {}
            for tRes in aW:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aW = []
            for k,v in dW.items():
                aT = list(v)
                aT.sort()
                aW.append({'pathid':k[0].split(':')[1], 'pathname':k[1], 'targets':aT}) ## fixed kegg_id as the link requires without "path:" at the beginning
            aKexp = aW[:]

            ## targets / predicted
            aTargets = list(set([a[0] for a in aImmStrict+aImm]))
            aW = T2W.objects.filter(target__in=aTargets).select_related('target', 'wikipath').values_list('wikipath__wikipathid', 'wikipath__wikipathname', 'target__id', 'target__symbol', 'target__tname').distinct()
            dW = {}
            for tRes in aW:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aW = []
            for k,v in dW.items():
                aT = list(v)
                aT.sort()
                aW.append({'pathid':k[0], 'pathname':k[1], 'targets':aT})
            aWpred = aW[:]

            aW = T2K.objects.filter(target__in=aTargets).select_related('target', 'kegg').values_list('kegg__keggid', 'kegg__keggname', 'target__id', 'target__symbol', 'target__tname').distinct()
            dW = {}
            for tRes in aW:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aW = []
            for k,v in dW.items():
                aT = list(v)
                aT.sort()
                aW.append({'pathid':k[0].split(':')[1], 'pathname':k[1], 'targets':aT}) ## fixed kegg_id as the link requires without "path:" at the beginning
            aKpred = aW[:]

            ## puch to session cash
            request.session['mirnas'][mid]['wikipath_exp'] = aWexp
            request.session['mirnas'][mid]['kegg_exp'] = aKexp
            request.session['mirnas'][mid]['wikipath_pred'] = aWpred
            request.session['mirnas'][mid]['kegg_pred'] = aKpred
            request.session.modified = True

        #return HttpResponse(sOut)

        context = {'wikipath_exp':aWexp, 'wikipath_pred':aWpred, 'kegg_exp':aKexp, 'kegg_pred':aKpred, 'type':sTYPE, 'existed':sPexisted}

        ## sent to differnt side, as it will be displayed in m.html in a tab
        return render(request, 'irndb2/mp.html', context)

    ## elif sTYPE == "r":
    ##     aFINAL = []
    ##     bTFBS = 0
    ##     # fetch primary for mirna
    ##     aPrimaries = MPRIMARY.objects.filter(mirna=mirna_obj).distinct()
    ##     # Fetch TFBS for primaries
    ##     aTFBS = MPRIMARY2TFBS.objects.filter(Q(mprimary__in=aPrimaries), Q(fdr__gt=-1) | Q(pvalue__gt=-1)).distinct()

    ##     for primary_obj in aPrimaries:
    ##         aTEMP = aTFBS.filter(mprimary=primary_obj).distinct()
    ##         for oMTFBS in aTEMP:  # hChIP was the wrong name for the source
    ##             if oMTFBS.experiment_source == 'hChIP':
    ##                 oMTFBS.experiment_source = 'htChIP'
    ##         if len(aTEMP)>0:
    ##             aFINAL.append(aTEMP)

    ##     if len(aFINAL) > 0:
    ##         bTFBS = 1
    ##     context = {'m':mirna_obj,
    ##                'aTFBS':aFINAL,
    ##                'bTFBS':bTFBS,
    ##                'type':sTYPE}

    ##     return render(request, 'irndb2/m_tfbs.html', context)

    elif sTYPE == "t": # target view
        # experiemtnal targets
        aTargetsExp = aImmStrictExp + aImmExp
        # predicted mouse targets
        aTargets = aImmStrict + aImm

        context = {'m':mirna_obj,
               'targets_imm':aTargets,
               'targets_imm_exp':aTargetsExp,
               'bM':bM,
               'type':sTYPE}

        return render(request, 'irndb2/mirna_targets.html', context)


def lncrna_method(request, sym, flush=True): # need to change to False for prod.
    """"""
    context = {}
    context["entity_type"] = "lncrna"
    
    ## flush the session store of pirna
    if flush:
        try:
            del request.session['lncrnas']
        except:
            request.session['lncrnas'] = {}
 
    # Need a store for pirnas if not already there
    if 'lncrnas' not in request.session:
        request.session['lncrnas'] = {}

    a = Lncrna.objects.filter(lsymbol__regex=r'^%s$'%sym) # exact match, kind of a hack as the __exact did not work
    if len(a)>1:
        context["error"] = 'Query "%s" resulted in more then 1 entitiy.'%sym
        return render(request, "irndb2/404.html", context)
    elif len(a)==0:
        context["error"] = 'Query "%s" resulted in 0 entities.'%sym
        return render(request, "irndb2/404.html", context)
    else:
        lncrna_obj = a[0]
        lid = lncrna_obj.id

    # lncRNA exists get some more info for lncRNA
    # target sources where lncRNA was inferred from
    res_list = L2T.objects.filter(lncrna=lncrna_obj).values_list('source').distinct().order_by('source')
    res_list = ','.join([t[0] for t in res_list])
    res_list = ', '.join(res_list.split(','))
    lncrna_obj.sources = res_list
    
    # adjust alias
    lncrna_obj.lalias = ', '.join(lncrna_obj.lalias.split(','))
    
    # fetch type via GET method
    sTYPE = request.GET.get('type', 'x') # some char not in use
    if sTYPE not in ["p","g","t"]: # add possible tabs here
        context['l'] = lncrna_obj
        context['aImmStrict'] = []
        context['aImm'] = []
        return render_to_response("irndb2/lncrna_base.html", context)

    bL = 0
    iExisted = 0
    ## check if lncrna still in session/cache if so, use existing and return
    if lid in request.session['lncrnas']:
        bL = 1
        aTargets = request.session['lncrnas'][lid]['targets']
        iExisted = 1
    else: # need to fetch targets of lncRNA
        aTargets = L2T.objects.filter(lncrna=lid).select_related('target').values_list('target',
                                                                              'target__symbol',
                                                                              'target__tname',
                                                                              'target__strict',
                                                                              'target__immusources',
                                                                              'pmid',
                                                                              'source').distinct().order_by('target__symbol')
        aTargets = list(aTargets)
        aTargetsFinal = []
        for t in aTargets:
            t = list(t)
            t[4] = [s.strip() for s in t[4].split(',')]
            aTargetsFinal.append(t)
            t[6] = ', '.join(t[6].split(','))
        aTargets = aTargetsFinal

        request.session['lncrnas'][lid] = {'targets':aTargets}
        request.session.modified = True

    #-- target tab --
    if sTYPE == "t":
        context['l'] = lncrna_obj
        context['targets'] = aTargets
        context['bL'] = bL
        context['existed'] = iExisted
        return render(request, 'irndb2/rna_targets.html', context)

    #-- GO tab --
    if sTYPE == 'g':
        ## fetch pathways from session cache if exists or create new
        if 'goprocess' in request.session['lncrnas'][lid]:
            aP  = request.session['lncrnas'][lid]['goprocess']
            aF  = request.session['lncrnas'][lid]['gofunction']
            iGexisted = 1
        else:
            iGexisted = 0
            aP = []
            aF = []

            aIDs = [t[0] for t in aTargets]
            aG = T2G.objects.filter(target__in=aIDs).select_related('target', 'go').values_list('go__goid', 'go__goname', 'go__gocat', 'target__id', 'target__symbol', 'target__tname').distinct()

            dGp = {}
            dGf = {}
            for tRes in aG:
                tG = (tRes[0], tRes[1])
                if tRes[2]=='Process':
                    if tG not in dGp:
                        dGp[tG] = set()
                    dGp[tG].add((tRes[4], tRes[3], tRes[5]))
                elif tRes[2]=='Function':
                    if tG not in dGf:
                        dGf[tG] = set()
                    dGf[tG].add((tRes[4], tRes[3], tRes[5]))

            aP = []
            for k,v in dGp.items():
                aT = list(v)
                aT.sort()
                aP.append({'goid':k[0], 'goname':k[1], 'targets':aT})
            aF = []
            for k,v in dGf.items():
                aT = list(v)
                aT.sort()
                aF.append({'goid':k[0], 'goname':k[1], 'targets':aT})


            request.session['lncrnas'][lid]['goprocess'] = aP
            request.session['lncrnas'][lid]['gofunction'] = aF
            request.session.modified = True

        context['go_p'] = aP
        context['go_f'] = aF
        context['existed'] = iGexisted
        return render(request, 'irndb2/rna_go.html', context)

    #-- pathway tab --
    elif sTYPE=="p":
        ## fetch pathways from session cache if exists or create new
        if 'wikipath' in request.session['lncrnas'][lid]:
            aW  = request.session['lncrnas'][lid]['wikipath']
            aK  = request.session['lncrnas'][lid]['kegg']
            iPexisted = 1
        else:
            ## create new
            iPexisted = 0
            # target ids
            aIDs = [t[0] for t in aTargets]
            # wikipath exp
            aWtemp = T2W.objects.filter(target__in=aIDs).select_related('target', 'wikipath').values_list('wikipath__wikipathid', 'wikipath__wikipathname', 'target__id', 'target__symbol', 'target__tname').distinct()
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list(v)
                aT.sort()
                aWtemp.append({'pathid':k[0], 'pathname':k[1], 'targets':aT})
            aW = aWtemp[:]

            aWtemp = T2K.objects.filter(target__in=aIDs).select_related('target', 'kegg').values_list('kegg__keggid', 'kegg__keggname', 'target__id', 'target__symbol', 'target__tname').distinct()
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list(v)
                aT.sort()
                aWtemp.append({'pathid':k[0].split(':')[1], 'pathname':k[1], 'targets':aT}) ## fixed kegg_id as the link requires without "path:" at the beginning
            aK = aWtemp[:]

            ## puch to session cash
            request.session['lncrnas'][lid]['wikipath'] = aW
            request.session['lncrnas'][lid]['kegg'] = aK
            request.session.modified = True

        context['wikipath'] = aW
        context['kegg'] = aK
        context['type'] = sTYPE
        context['existed'] = iPexisted
        return render(request, 'irndb2/rna_pathways.html', context)


def pirna_method(request, name, flush=True): # need to change to False for prod.
    """"""
    context = {}
    context['entity_type'] = 'pirna'
    
    ## ## flush the session store of pirna
    if flush:
        try:
            del request.session['pirnas']
        except:
            request.session['pirnas'] = {}
 
    # Need a store for pirnas if not already there
    if 'pirnas' not in request.session:
        request.session['pirnas'] = {}

    a = Pirna.objects.filter(pname__regex=r'^%s$'%name) # exact match, kind of a hack as the __exact did not work
    if len(a)>1:
        context["error"] = 'Query "%s" resulted in more then 1 entitiy.'%name
        return render(request, "irndb2/404.html", context)
    elif len(a)==0:
        context["error"] = 'Query "%s" resulted in 0 entities.'%name
        return render(request, "irndb2/404.html", context)
    else:
        pirna_obj = a[0]
        pid = pirna_obj.id
  
    ## some more infomation about pirna
    pirna_obj.paccession_link = 'http://www.ncbi.nlm.nih.gov/nuccore/'+'%2C'.join(pirna_obj.paccession.split(','))
    pirna_obj.paccession = ', '.join(pirna_obj.paccession.split(','))
    #http://www.ncbi.nlm.nih.gov/pubmed/?term=8751592[uid]+OR+16204232[uid]+OR+23931754[uid]
    aPMID = [s.strip() for s in pirna_obj.ppmid.split(',')]
    sLink = 'http://www.ncbi.nlm.nih.gov/pubmed/?term='
    for i in xrange(len(aPMID)):
        if i+1 < len(aPMID):
            sLink += '%s[uid]+OR+'%(aPMID[i])
        else:
            sLink += '%s[uid]'%(aPMID[i]) # last one
    pirna_obj.ppmid_link = sLink
    pirna_obj.ppmid = ', '.join(pirna_obj.ppmid.split(','))
    pirna_obj.palias = ', '.join(pirna_obj.palias.split(','))
    # currently only one source
    ## TODO: Needs changes in db structure to dad more sources
    pirna_obj.psource = 'piRBase'

    # fetch type via GET method
    sTYPE = request.GET.get('type', 'x') # some char not in use
    if sTYPE not in ["p","g","t"]: # add possible tabs here
        context['p'] = pirna_obj
        context['aImmStrict'] = []
        context['aImm'] = []
        return render_to_response("irndb2/pirna_base.html", context)

    bL = 0
    iExisted = 0
    ## check if pirna still in session/cache if so, use existing and return
    if pid in request.session['pirnas']:
        bL = 1
        aTargets = request.session['pirnas'][pid]['targets']
        iExisted = 1
    else: # need to fetch targets of pirna
        aTargets = P2T.objects.filter(pirna=pid).select_related('target').values_list('target',
                                                                              'target__symbol',
                                                                              'target__tname',
                                                                              'target__strict',
                                                                              'target__immusources',
                                                                              'pmid',
                                                                              'experimenttype').distinct().order_by('target__symbol')

        aTargets = list(aTargets)
        aTargetsFinal = []
        aTargets = list(aTargets)
        for t in aTargets:
            t = list(t)
            t[4] = [s.strip() for s in t[4].split(',')]
            aTargetsFinal.append(t)
        aTargets = aTargetsFinal

        request.session['pirnas'][pid] = {'targets':aTargets}
        request.session.modified = True
        ##return HttpResponse(aTargets)

    #-- target tab --
    if sTYPE == "t":
        context['p'] = pirna_obj
        context['targets'] = aTargets
        context['bL'] = bL
        context['existed'] = iExisted
        return render(request, 'irndb2/rna_targets.html', context)

    #-- GO tab --
    if sTYPE == 'g':
        ## fetch pathways from session cache if exists or create new
        if 'goprocess' in request.session['pirnas'][pid]:
            aP  = request.session['pirnas'][pid]['goprocess']
            aF  = request.session['pirnas'][pid]['gofunction']
            iGexisted = 1
        else:
            iGexisted = 0
            aP = []
            aF = []

            aIDs = [t[0] for t in aTargets]
            aG = T2G.objects.filter(target__in=aIDs).select_related('target', 'go').values_list('go__goid', 'go__goname', 'go__gocat', 'target__id', 'target__symbol', 'target__tname').distinct()

            dGp = {}
            dGf = {}
            for tRes in aG:
                tG = (tRes[0], tRes[1])
                if tRes[2]=='Process':
                    if tG not in dGp:
                        dGp[tG] = set()
                    dGp[tG].add((tRes[4], tRes[3], tRes[5]))
                elif tRes[2]=='Function':
                    if tG not in dGf:
                        dGf[tG] = set()
                    dGf[tG].add((tRes[4], tRes[3], tRes[5]))

            aP = []
            for k,v in dGp.items():
                aT = list(v)
                aT.sort()
                aP.append({'goid':k[0], 'goname':k[1], 'targets':aT})
            aF = []
            for k,v in dGf.items():
                aT = list(v)
                aT.sort()
                aF.append({'goid':k[0], 'goname':k[1], 'targets':aT})


            request.session['pirnas'][pid]['goprocess'] = aP
            request.session['pirnas'][pid]['gofunction'] = aF
            request.session.modified = True

        context['go_p'] = aP
        context['go_f'] = aF
        context['existed'] = iGexisted
        return render(request, 'irndb2/rna_go.html', context)

    #-- pathway tab --
    elif sTYPE=="p":
        ## fetch pathways from session cache if exists or create new
        if 'wikipath' in request.session['pirnas'][pid]:
            aW  = request.session['pirnas'][pid]['wikipath']
            aK  = request.session['pirnas'][pid]['kegg']
            iPexisted = 1
        else:
            ## create new
            iPexisted = 0
            # target ids
            aIDs = [t[0] for t in aTargets]
            # wikipath exp
            aWtemp = T2W.objects.filter(target__in=aIDs).select_related('target', 'wikipath').values_list('wikipath__wikipathid', 'wikipath__wikipathname', 'target__id', 'target__symbol', 'target__tname').distinct()
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list(v)
                aT.sort()
                aWtemp.append({'pathid':k[0], 'pathname':k[1], 'targets':aT})
            aW = aWtemp[:]

            aWtemp = T2K.objects.filter(target__in=aIDs).select_related('target', 'kegg').values_list('kegg__keggid', 'kegg__keggname', 'target__id', 'target__symbol', 'target__tname').distinct()
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list(v)
                aT.sort()
                aWtemp.append({'pathid':k[0].split(':')[1], 'pathname':k[1], 'targets':aT}) ## fixed kegg_id as the link requires without "path:" at the beginning
            aK = aWtemp[:]

            ## puch to session cash
            request.session['pirnas'][pid]['wikipath'] = aW
            request.session['pirnas'][pid]['kegg'] = aK
            request.session.modified = True

        context['wikipath'] = aW
        context['kegg'] = aK
        context['type'] = sTYPE
        context['existed'] = iPexisted
        return render(request, 'irndb2/rna_pathways.html', context)


def kegg_method(request, id):
    context = {}
    return render(request, "irndb2/contact.html", context)


def wp_method(request, id):
    context = {}
    return render(request, "irndb2/contact.html", context)


def search_method(request):
    context = {}
    if request.method == 'GET':
        query = request.GET.get('q')
        if query:
            context["search_term"] = query
            # use "query" to look up things and store in "result"
            
            ## context["search_term"] = query
            ## # use "query" to look up things and store in "result"
            res_target = Target.objects.filter( Q(tname__icontains=query) | \
                                        Q(symbol__icontains=query) | \
                                        Q(id__icontains=query)
                                        ).values_list('id',
                                                      'symbol',
                                                      'tname').distinct()

            res_mirna = Mirna.objects.filter( Q(mname__icontains=query) | \
                                        Q(mirbase_id__icontains=query)
                                        ).values_list('id',
                                                      'mirbase_id',
                                                      'mname').distinct()

            res_lncrna = Lncrna.objects.filter( Q(lname__icontains=query) | \
                                                Q(lsymbol__icontains=query) | \
                                                Q(lalias__icontains=query) | \
                                                Q(lgeneid__icontains=query)
                                        ).values_list('id',
                                                      'lsymbol',
                                                      'lgeneid',
                                                      'lname',
                                                      'lalias').distinct()
            res_pirna = Pirna.objects.filter( Q(pname__icontains=query) | \
                                              Q(palias__icontains=query) | \
                                              Q(paccession__icontains=query)
                                        ).values_list('id',
                                                      'palias',
                                                      'pname',
                                                      'paccession').distinct()

            context["search_target"] = res_target
            context["search_mirna"] = res_mirna
            context["search_lncrna"] = res_lncrna
            context["search_pirna"] = res_pirna
            context["search_results"] = len(res_target) + len(res_mirna) + len(res_lncrna) + len(res_pirna)
            cat_num = 0
            for res in [res_target, res_mirna, res_lncrna, res_pirna]:
                if len(res) > 0:
                    cat_num += 1
            context["search_cat"] = cat_num
            
        else:
            context["search_term"] = "No term entered."
            context["search_results"] = 0
            
        return render(request, 'irndb2/search.html', context)
    # if not GET method return homepage
    else:
        return render(request, "irndb2/home.html", context)

def home_method(request):
    context = {}
    context['num_target'] = Target.objects.all().count()
    context['num_mirna'] = Mirna.objects.all().count()
    context['num_lncrna'] = Lncrna.objects.all().count()
    context['num_pirna'] = Pirna.objects.all().count()
    return render(request, "irndb2/home.html", context)


def contact_method(request):
    context = {}
    return render(request, "irndb2/contact.html", context)


def target_method(request, sym):
    context = {}
    a = Target.objects.filter(symbol__regex=r'^%s$'%sym) # exact match, kind of a hack as the __exact did not work
    if len(a)>1:
        context["error"] = 'Query "%s" resulted in more then 1 entitiy.'%sym
        return render(request, "irndb2/404.html", context)
    elif len(a)==0:
        context["error"] = 'Query "%s" resulted in 0 entities.'%sym
        return render(request, "irndb2/404.html", context)
    else:
        obj = a[0]
    
    return render(request, "irndb2/target.html", context)





def doc_method(request):
    context = {}
    tab = request.GET.get('tab', 'x')
    context = {}
    if tab not in ['1','2','3','4']:
        return render(request, "irndb2/doc.html", context)
    elif tab == '1':
        return render(request, "irndb2/doc_overview.html", context)
    elif tab == '2':
        return render(request, "irndb2/doc_desc.html", context)
    elif tab == '3':
        return render(request, "irndb2/doc_resources.html", context)
    elif tab == '4':
        # fetch stats from db
        num_m2t_exp_mmuhsa = M2T_EXP.objects.filter(target__strict__gt=-1).values_list('mirna_id', 'target_id').distinct().count()
        num_m_exp_mmuhsa = M2T_EXP.objects.filter(target__strict__gt=-1).values_list('mirna_id').distinct().count()
        num_t_exp_mmuhsa = M2T_EXP.objects.filter(target__strict__gt=-1).values_list('target_id').distinct().count()

        num_m2t_exp_mmu = M2T_EXP.objects.filter(target__strict = 1).values_list('mirna_id', 'target_id').distinct().count()
        num_m_exp_mmu = M2T_EXP.objects.filter(target__strict = 1).values_list('mirna_id').distinct().count()
        num_t_exp_mmu = M2T_EXP.objects.filter(target__strict = 1).values_list('target_id').distinct().count()


        num_m2t_pred_mmuhsa = M2T_PRED.objects.filter(target__strict__gt=-1).values_list('mirna_id', 'target_id').distinct().count()
        num_m_pred_mmuhsa = M2T_PRED.objects.filter(target__strict__gt=-1).values_list('mirna_id').distinct().count()
        num_t_pred_mmuhsa = M2T_PRED.objects.filter(target__strict__gt=-1).values_list('target_id').distinct().count()

        num_m2t_pred_mmu = M2T_PRED.objects.filter(target__strict = 1).values_list('mirna_id', 'target_id').distinct().count()
        num_m_pred_mmu = M2T_PRED.objects.filter(target__strict = 1).values_list('mirna_id').distinct().count()
        num_t_pred_mmu =M2T_PRED.objects.filter(target__strict = 1).values_list('target_id').distinct().count()

        num_l2t_mmu = L2T.objects.filter(target__strict = 1).values_list('lncrna_id','target_id').distinct().count()
        num_l2t_mmuhsa =  L2T.objects.filter(target__strict__gt = -1).values_list('lncrna_id','target_id').distinct().count()

        num_l2t_pirna_mmu = L2T.objects.filter(target__strict = 1).values_list('lncrna_id').distinct().count()
        num_l2t_pirna_mmuhsa =  L2T.objects.filter(target__strict__gt = -1).values_list('lncrna_id').distinct().count()

        num_l2t_target_mmu = L2T.objects.filter(target__strict = 1).values_list('target_id').distinct().count()
        num_l2t_target_mmuhsa =  L2T.objects.filter(target__strict__gt = -1).values_list('target_id').distinct().count()


        num_p2t_mmu = P2T.objects.filter(target__strict = 1).values_list('pirna_id','target_id').distinct().count()
        num_p2t_mmuhsa = P2T.objects.filter(target__strict__gt = -1).values_list('pirna_id','target_id').distinct().count()


        num_p2t_pirna_mmu = P2T.objects.filter(target__strict = 1).values_list('pirna_id',).distinct().count()
        num_p2t_pirna_mmuhsa = P2T.objects.filter(target__strict__gt = -1).values_list('pirna_id').distinct().count()


        num_p2t_target_mmu = P2T.objects.filter(target__strict = 1).values_list('target_id').distinct().count()
        num_p2t_target_mmuhsa = P2T.objects.filter(target__strict__gt = -1).values_list('target_id').distinct().count()


        context = {
                   'num_m2t_exp_mmuhsa':num_m2t_exp_mmuhsa,
                   'num_m_exp_mmuhsa':num_m_exp_mmuhsa,
                   'num_t_exp_mmuhsa':num_t_exp_mmuhsa,
                   'num_m2t_exp_mmu':num_m2t_exp_mmu,
                   'num_m_exp_mmu':num_m_exp_mmu,
                   'num_t_exp_mmu':num_t_exp_mmu,
                   'num_m2t_pred_mmuhsa':num_m2t_pred_mmuhsa,
                   'num_m_pred_mmuhsa':num_m_pred_mmuhsa,
                   'num_t_pred_mmuhsa':num_t_pred_mmuhsa,
                   'num_m2t_pred_mmu':num_m2t_pred_mmu,
                   'num_m_pred_mmu':num_m_pred_mmu,
                   'num_t_pred_mmu':num_t_pred_mmu,
                   'num_l2t_mmu': num_l2t_mmu,
                   'num_l2t_mmuhsa': num_l2t_mmuhsa,
                   'num_l2t_pirna_mmu':num_l2t_pirna_mmu,
                   'num_l2t_pirna_mmuhsa':num_l2t_pirna_mmuhsa,
                   'num_l2t_target_mmu':num_l2t_target_mmu,
                   'num_l2t_target_mmuhsa':num_l2t_target_mmuhsa,
                   'num_p2t_mmu': num_p2t_mmu,
                   'num_p2t_mmuhsa': num_p2t_mmuhsa,
                   'num_p2t_pirna_mmu':num_p2t_pirna_mmu,
                   'num_p2t_pirna_mmuhsa':num_p2t_pirna_mmuhsa,
                   'num_p2t_target_mmu':num_p2t_target_mmu,
                   'num_p2t_target_mmuhsa':num_p2t_target_mmuhsa
                   }

        return render(request, "irndb2/doc_stats.html", context)
    else:
        return render(request, "irndb2/doc.html", context)

    
def browse_method(request):
    dnl = request.GET.get('dnl', '0')
    filename = request.GET.get('f','data.csv')
    entitytype = request.GET.get('type', '0')
    pathway = request.GET.get('pw', '0')
    pathwaytype = request.GET.get('pwt', 'x')
    
    context = {}
    context["entity_type"] = entitytype
    context["pwt"] = pathwaytype
    if entitytype == 'mirna':
        context["rna_title"] = "miRNA"

        # download instead of display
        if dnl == '1' and pathway != '1':  
            query_set = Mirna.objects.filter(num_immune__gt=0).distinct()
            data = create_data_mirna(query_set, 0)
            response = create_dnl_response(filename, data, ['Name','ID','NumExperimentalMouseImmuneTargets','NumPredictedMouseImmuneTargets','NumExperimentalHumanInferredImmuneTargets','NumPredictedHumanInferredImmuneTargets'])
            return response
        
        # browse pathways instead --> return pathway list
        elif pathway == '1':
            if pathwaytype not in ["wikipathway","kegg"]:
                return render_to_response("irndb2/browsepw.html", context)
            else:
                # all t2l object
                rna2t_list = M2T_EXP.objects.all().select_related('mirna','target').distinct()
                #rna2t_list = M2T_EXP.objects.filter(target__strict = 1).select_related('mirna','target').distinct()
                if dnl == '1':
                    res_list = get_pathways(entitytype, pathwaytype, '1')
                    response = create_dnl_response(filename, res_list, ['Pathway_name', 'Pathway_id', 'Target', 'RNAs'])
                    return response
                else:
                    res_list = get_pathways(entitytype, pathwaytype, '0')
                    context["data"] = res_list
                    return render(request, "irndb2/browsepw_content.html", context)
                
        # no download --> browse mirnas
        else:  
            query_set = Mirna.objects.filter(num_immune__gt=0).distinct()
            context['data'] = create_data_mirna(query_set, 1)
            return render(request, "irndb2/browse_mirna.html", context)
    
    elif entitytype == 'target':
        if dnl == '1' and pathway != '1':  # download instead of display
            query_set = Target.objects.all().distinct()
            data = create_data_targets(query_set, 0)
            response = create_dnl_response(filename, data,['symbol', 'name', 'geneid', 'ImmuneRelevanceInferredFrom', 'num_exp_miRNA', 'num_pred_miRNA', 'num_lncRNA', 'num_piRNA'])
            return response
        else:  # no download
            query_set = Target.objects.all().distinct()
            context['data'] = create_data_targets(query_set)
            return render(request, "irndb2/browse_target.html", context)

    elif entitytype == 'lncrna':
        context["rna_title"] = "lncRNA"
        if dnl == '1' and pathway != '1':  # download instead of display
            query_set = Lncrna.objects.all().distinct()
            data = create_data_lncrna(query_set, 0)
            response = create_dnl_response(filename, data, ['symbol', 'name', 'alias',  'NumMouseInferredImmuneTargets', 'NumHumanInferredImmuneTargets'])
            return response
        
        # browse pathways instead --> return pathway list
        elif pathway == '1':
            if pathwaytype not in ["wikipathway","kegg"]:
                return render_to_response("irndb2/browsepw.html", context)
            else:
                # all t2l object
                rna2t_list = L2T.objects.all().select_related('lncrna','target').distinct()
                # get list of pathways
                if dnl == '1':
                    res_list = get_pathways(entitytype, pathwaytype, '1')
                    response = create_dnl_response(filename, res_list, ['Pathway_name', 'Pathway_id', 'Target', 'RNAs'])
                    return response
                else:
                    res_list = get_pathways(entitytype, pathwaytype, '0')
                    context["data"] = res_list
                    return render(request, "irndb2/browsepw_content.html", context)

            
        else:  # no download
            query_set = Lncrna.objects.all().distinct()
            context['data'] = create_data_lncrna(query_set)
            return render(request, "irndb2/browse_lncrna.html", context)

    elif entitytype == 'pirna':
        context["rna_title"] = "piRNA"
        aQS = P2T.objects.all().select_related('pirna', 'target')
        if dnl == '1' and pathway != '1':  # download instead of display
            query_set = Pirna.objects.all().distinct()
            data = create_data_pirna(query_set, 0)
            response = create_dnl_response(filename, data, ['name', 'alias', 'accession',  'NumMouseInferredImmuneTargets',
             'NumHumanInferredImmuneTargets'])
            return response
        
        # browse pathways instead --> return pathway list
        elif pathway == '1':
            if pathwaytype not in ["wikipathway","kegg"]:
                return render_to_response("irndb2/browsepw.html", context)
            else:
                rnasymbol = "pirna__pname"
                # get list of pathways
                if dnl == '1':
                    res_list = get_pathways(entitytype, pathwaytype, '1')
                    response = create_dnl_response(filename, res_list, ['Pathway_name', 'Pathway_id', 'Target', 'RNAs'])
                    return response
                else:
                    res_list = get_pathways(entitytype, pathwaytype, '0')
                    context["data"] = res_list
                    return render(request, "irndb2/browsepw_content.html", context)

        else:
            query_set = Pirna.objects.all().distinct()
            context['data'] = create_data_pirna(query_set)
            return render(request, "irndb2/browse_pirna.html", context)

    else:
        return render(request, "irndb2/home.html", context)

    
def tables_method(request):
    context = {}
    return render(request, "irndb2/tables.html", context)


def charts_method(request):
    context = {}
    return render(request, "irndb2/charts.html", context)


#----------------------------------------------------------------
# NON-VIEW methods
#----------------------------------------------------------------
def create_data_pirna(entity_list, links=1):
    data = []
    for e in entity_list:
        alias = ', '.join(e.palias.split(','))
        acc_str = ', '.join(e.paccession.split(','))
        if links==1:
            name_str = '<a class="m1" href="%s/pirna/%s" title="Link to IRNdb piRNA entry">%s</a>' % (_APP_LINK_PREFIX,
                                                                                                          e.pname,
                                                                                                          e.pname)
            acc_str = '<a class="m1" href="http://www.ncbi.nlm.nih.gov/nuccore/%s" title="Link to NCBI">%s</a>' % (e.paccession, acc_str)
        else:
            name_str = e.pname
            
        aTemp = [
            name_str,
            alias,
            acc_str,
            e.num_targets_mmu,
            e.num_targets_hsa
            ]
        a = [str(s) for s in aTemp]
        data.append(a)
    return data


def create_data_lncrna(entity_list, links=1):
    data = []
    for e in entity_list:
        num_immune_hsa  = e.num_immune - e.num_immune_strict
        alias = ', '.join(e.lalias.split(','))

        if links==1:
            symbol_str = '<a class="m1" href="%s/lncrna/%s" title="Link to IRNdb lncRNA entry">%s</a>' % (_APP_LINK_PREFIX,
                                                                                                          e.lsymbol,
                                                                                                          e.lsymbol)
            name_str = '<a class="m1" href="%s" title="Link to NCBI gene">%s</a>' % (e.llink, e.lname)
            alias_str = '<a class="m1" href="%s" title="Link to NCBI gene">%s</a>' % (e.llink, alias)
        else:
            symbol_str = e.lsymbol
            name_str = e.lname
            alias_str = alias
        aTemp = [
            symbol_str,
            name_str,
            alias_str,
            e.num_immune_strict,
            num_immune_hsa
            ]
        a = [str(s) for s in aTemp]
        data.append(a)
    return data


def create_data_targets(entity_list, links=1):
    data = []
    for e in entity_list:
       
        # symbol, name, geneid, species, num_exp_mirna, num_pred_mirna, num_lncrna, num_piRNA
        if links==1:
            symbol_str = '<a class="t1" href="%s/target/%s" title="Link to IRNdb target entry">%s</a>' % (_APP_LINK_PREFIX,
                                                                                                          e.symbol,
                                                                                                          e.symbol)
            name_str = '<a class="t1" href="http://www.ncbi.nlm.nih.gov/gene/%s" title="Link to NCBI gene">%s</a>' % (e.id, e.tname)
            geneid_str = '<a class="t1" href="http://www.ncbi.nlm.nih.gov/gene/%s" title="Link to NCBI gene">%s</a>' % (e.id, e.id)
        else:
            symbol_str = e.symbol
            name_str = e.tname
            geneid_str = e.id

        if e.strict == 1:
            species = 'mouse'
        else:
            species = 'human'
        aTemp = [
            symbol_str,
            name_str,
            geneid_str,
            species,
            e.num_mirnas_exp,
            e.num_mirnas_pred,
            e.num_lncrnas,
            e.num_pirnas
            ]
        a = [str(s) for s in aTemp]
        data.append(a)
    return data


def create_data_mirna(entity_list, links=1):
    data = []
    for e in entity_list:
        e.num_exp_hsa  = e.num_immune_exp - e.num_immune_strict_exp # verified targets with immune relevance inferred from humans.
        e.num_pred_mmu = e.num_immune_strict - e.num_immune_strict_exp
        e.num_pred_hsa = e.num_immune - e.num_pred_mmu - e.num_exp_hsa - e.num_immune_strict_exp  # predicted targets with immune relevance inferred from humans.
        if links==1:
            mirna_str = '<a class="m1" href="%s/mirna/%s" title="IRN miRNA details">%s</a>' % (_APP_LINK_PREFIX,
                                                                                               e.mname,
                                                                                               e.mname)
            mirnaid_str = '<a class="m1" href="http://mirbase.org/cgi-bin/mature.pl?mature_acc=%s" title="Open miRNA in mirBase">%s</a>' % (e.mirbase_id, e.mirbase_id)
        else:
            mirna_str = e.mname
            mirnaid_str = e.mirbase_id

        aTemp = [
            mirna_str,
            mirnaid_str,
            e.num_immune_strict_exp,
            e.num_pred_mmu,
            e.num_exp_hsa,
            e.num_pred_hsa
            ]
        a = [str(s) for s in aTemp]
        data.append(a)
    return data


def create_dnl_response(filename, data, header):
    data = [header] + data
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    writer = csv.writer(response)
    for row in data:
        writer.writerow(row)
    return response


def get_pathways(entitytype, pathwaytype, dnl='0'):
    rnalink_template = '<a class="m1" href="%s/%s/%s">%s</a>' # _APP_LINK_PREFIX, rnatype, rnasymbol/name, symbol/name
    pwlink_template = '<a title="Open in IRNdb" class="g" href="%s/%s/%s">%s</a>' # _APP_LINK_PREFIX, pathwaytype, pwid, pwname
    targetlink_template = '<a title="Open in IRNdb" class="t1" href="%s/target/%s">%s</a>' # _APP_LINK_PREFIX, symbol, symbol 
  
    dPW = {}
    res_list = []
    if pathwaytype == 'kegg':
        if entitytype == 'pirna':
            t2pw_list = T2K.objects.filter(~Q(pirna = '0')).select_related('target', 'kegg').distinct()
        elif entitytype == 'lncrna':
            t2pw_list = T2K.objects.filter(~Q(lncrna = '0')).select_related('target', 'kegg').distinct()
        elif entitytype == 'mirna':
            t2pw_list = T2K.objects.filter(~Q(mirna_exp = '0')).select_related('target', 'kegg').distinct()

        for t2pw in t2pw_list:
            if t2pw.kegg not in dPW:
                dPW[t2pw.kegg] = []

            if dnl != '1':
                if entitytype == 'pirna':
                    rnas = '; '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.pirna.split(',')])
                elif entitytype == 'lncrna':
                    rnas = '; '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.lncrna.split(',')])
                elif entitytype == 'mirna':
                    rnas = '; '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.mirna_exp.split(',')])


                dPW[t2pw.kegg].append([ str(targetlink_template % (_APP_LINK_PREFIX,
                                                                   t2pw.target.symbol,
                                                                   t2pw.target.symbol)),
                                                                   rnas])
            else:
                if entitytype == 'pirna':
                    rnas = str(t2pw.pirna)
                elif entitytype == 'lncrna':
                    rnas = str(t2pw.lncrna)
                elif entitytype == 'mirna': 
                    rnas = str(t2pw.mirna_exp)

                dPW[t2pw.kegg].append([ str(t2pw.target.symbol), rnas])

        for kegg, targetlist in dPW.items():
            if dnl != '1':
                targetlist.sort()
                str_table = '<table><tbody>'
                for t_entry in targetlist:
                    row_str = '<tr><td style="width:120px; vertical-align: top;">%s</td><td>%s</td></tr>' % (t_entry[0], t_entry[1])
                    str_table += row_str
                str_table += '</tbody></table>'
                res_list.append([str(pwlink_template % (_APP_LINK_PREFIX,
                                                        pathwaytype,
                                                        str(kegg.keggid),
                                                        str(kegg.keggname))), str_table])
            else:
                # here make one row per target
                for tlist in targetlist:
                    res_list.append([str(kegg.keggname), str(kegg.keggid), tlist[0], tlist[1]])
        
    elif pathwaytype == 'wikipathway':
        if entitytype == 'pirna':
            t2pw_list = T2W.objects.filter(~Q(pirna = '0')).select_related('target', 'wikipath').distinct()
        elif entitytype == 'lncrna':
            t2pw_list = T2W.objects.filter(~Q(lncrna = '0')).select_related('target', 'wikipath').distinct()
        elif entitytype == 'mirna':
            t2pw_list = T2W.objects.filter(~Q(mirna_exp = '0')).select_related('target', 'wikipath').distinct()

        for t2pw in t2pw_list:
            if t2pw.wikipath not in dPW:
                dPW[t2pw.wikipath] = []

            if dnl != '1':
                if entitytype == 'pirna':
                    rnas = '; '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.pirna.split(',')])
                elif entitytype == 'lncrna':
                    rnas = '; '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.lncrna.split(',')])
                elif entitytype == 'mirna':
                    rnas = '; '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.mirna_exp.split(',')])


                dPW[t2pw.wikipath].append([ str(targetlink_template % (_APP_LINK_PREFIX,
                                                                       t2pw.target.symbol,
                                                                       t2pw.target.symbol)),
                                                                       rnas])
            else:
                if entitytype == 'pirna':
                    rnas = str(t2pw.pirna)
                elif entitytype == 'lncrna':
                    rnas = str(t2pw.lncrna)
                elif entitytype == 'mirna': 
                    rnas = str(t2pw.mirna_exp)

                dPW[t2pw.wikipath].append([ str(t2pw.target.symbol), rnas])

        for wp, targetlist in dPW.items():
            if dnl != '1':
                targetlist.sort()
                str_table = '<table><tbody>'
                for t_entry in targetlist:
                    row_str = '<tr><td style="width:120px; vertical-align: top;">%s</td><td>%s</td></tr>' % (t_entry[0], t_entry[1])
                    str_table += row_str
                str_table += '</tbody></table>'
                res_list.append([str(pwlink_template % (_APP_LINK_PREFIX,
                                                        pathwaytype,
                                                        str(wp.wikipathid),
                                                        str(wp.wikipathname))), str_table])
            else:
                # here make one row per target
                for tlist in targetlist:
                    res_list.append([ str(wp.wikipathid), str(wp.wikipathname), tlist[0], tlist[1]])

    return res_list
