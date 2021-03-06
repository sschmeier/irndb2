from django.shortcuts import render, render_to_response
from django.http import HttpResponse
from django.db.models import Q, F, Count
import csv, re

from .models import Target, T2G, T2K, T2W, T2R, T2C7, Go, Reactome, Kegg, Wikipath, Msigdb_c7, Mirna, M2T_EXP, M2T_PRED, Lncrna, L2T, Pirna, P2T, M2EXPR, MPRIMARY2MATURE, MPRIMARY2TFBS

# GLOBAL VARIABLE: change according to the url.py of the main project
# e.g. url(r'^apps/irndb/', include('irndb2.urls', namespace="irndb2")),
_APP_LINK_PREFIX = '/irndb'

#----------------------------------------------------------------
# VIEW methods
#----------------------------------------------------------------
def pw_method(request, id):
    """ Pathway method """
    context = {}
    ## get pw type
    res = re.search('^WP', id)
    res2 = re.search('^R\-', id)
    if res:
        pathwaytype = 'Wikipathways'
    elif res2:
        pathwaytype = 'REACTOME'
    else:
        pathwaytype = 'KEGG'

    context["pwt"] = pathwaytype

    if pathwaytype == 'KEGG':
        p = Kegg.objects.filter(keggid=id)
    elif pathwaytype == 'REACTOME':
        p = Reactome.objects.filter(pathid=id)
    else:
        p = Wikipath.objects.filter(wikipathid=id)
        
    if not p.exists(): ## empty list, pathway not found, exists should be better...
        context["error"] = 'Query "%s" resulted in no %s pathway.' % (id, pathwaytype)
        return render(request, "irndb2/404.html", context)
    elif p.count() > 1:
        context["error"] = 'Query "%s" resulted in more than one %s pathway.' % (id, pathwaytype)
        return render(request, "irndb2/404.html", context)
    else:
        pw_obj = p[0]  # hits the DB
        context['p'] = pw_obj
        if pathwaytype == 'KEGG':
            context['pathid'] = pw_obj.keggid.split(':')[1].strip()
        elif pathwaytype == 'REACTOME':
            context['pathid'] = pw_obj.pathid
        else:
            context['pathid'] = pw_obj.wikipathid

    target_url_str = '<a class="t1" href="%s/target/%s" title="Link to IRNdb target entry">%s</a>'
    pirna_url_str = '<a class="m1" href="%s/pirna/%s" title="Link to IRNdb piRNA entry">%s</a>' 
    lncrna_url_str = '<a class="m1" href="%s/lncrna/%s" title="Link to IRNdb lncRNA entry">%s</a>'
    mirna_url_str = '<a class="m1" href="%s/mirna/%s" title="IRN miRNA details">%s</a>'
        
    url_type = request.GET.get('type', 'x')
    if url_type == "target":

        if pathwaytype == 'KEGG':
            t2p_list = T2K.objects.filter(kegg=pw_obj).select_related('target').distinct()
        elif pathwaytype == 'REACTOME':
            t2p_list = T2R.objects.filter(path=pw_obj).select_related('target').distinct()
        else:
            t2p_list = T2W.objects.filter(wikipath=pw_obj).select_related('target').distinct()

        results_list = []
        for t2p in t2p_list:
            mexp_list = []
            mirna_str1 = ''
            if t2p.mirna_exp != '0':
                mirna_str1 = ',<br>'.join([mirna_url_str % (_APP_LINK_PREFIX, s, s) for s in str(t2p.mirna_exp).split(',')])
            mirna_str2 = ''
            if t2p.mirna_pred != '0':
                mirna_str2 = ',<br>'.join([mirna_url_str % (_APP_LINK_PREFIX, s, s) for s in str(t2p.mirna_pred).split(',')])
            lncrna_str = ''
            if t2p.lncrna != '0':
                lncrna_str = ',<br>'.join([lncrna_url_str % (_APP_LINK_PREFIX, s, s) for s in str(t2p.lncrna).split(',')])
            pirna_str = ''
            if t2p.pirna != '0':
                pirna_str = ',<br>'.join([pirna_url_str % (_APP_LINK_PREFIX, s, s) for s in str(t2p.pirna).split(',')])

            symbol = str(t2p.target.symbol)
            symbol_str = target_url_str % (_APP_LINK_PREFIX, symbol, symbol)
            results_list.append([symbol_str, mirna_str1, mirna_str2, lncrna_str, pirna_str])
        
        context['data'] = results_list
        return render_to_response("irndb2/pathway_target.html", context)
    
    elif url_type == 'lncrna':
        if pathwaytype == 'KEGG':
            t2p_list = T2K.objects.filter(Q(kegg = pw_obj) & ~Q(lncrna = '0')).select_related('target').distinct()
        elif pathwaytype == 'REACTOME':
            t2p_list = T2R.objects.filter(Q(path = pw_obj) & ~Q(lncrna = '0')).select_related('target').distinct()
        else:
            t2p_list = T2W.objects.filter(Q(wikipath = pw_obj) & ~Q(lncrna = '0')).select_related('target').distinct()
            
        dict_l2t = {}
        for t2p in t2p_list:
            for lncrna in t2p.lncrna.split(','):
                dict_l2t[lncrna] = dict_l2t.get(lncrna, []) + [str(t2p.target.symbol)]
                
        results_list = []
        for lncrna, target_list in dict_l2t.items():
            target_list = list(set(target_list))
            target_list.sort()
            target_str = ', '.join([target_url_str % (_APP_LINK_PREFIX, s, s) for s in target_list])

            lncrna_str = lncrna_url_str % (_APP_LINK_PREFIX, str(lncrna), str(lncrna))
            results_list.append([lncrna_str, target_str, str(len(target_list))])
  
        context['data'] = results_list
        return render_to_response("irndb2/pathway_lncrna.html", context)
    
    elif url_type == 'pirna':
        if pathwaytype == 'KEGG':
            t2p_list = T2K.objects.filter(Q(kegg = pw_obj) & ~Q(pirna = '0')).select_related('target').distinct()
        elif pathwaytype == 'REACTOME':
            t2p_list = T2R.objects.filter(Q(path = pw_obj) & ~Q(pirna = '0')).select_related('target').distinct()
        else:
            t2p_list = T2W.objects.filter(Q(wikipath = pw_obj) & ~Q(pirna = '0')).select_related('target').distinct()
            
        dict_l2t = {}
        for t2p in t2p_list:
            for pirna in t2p.pirna.split(','):
                dict_l2t[pirna] = dict_l2t.get(pirna, []) + [str(t2p.target.symbol)]
                
        results_list = []
        for pirna, target_list in dict_l2t.items():
            target_list = list(set(target_list))
            target_list.sort()
            target_str = ', '.join([target_url_str % (_APP_LINK_PREFIX, s, s) for s in target_list])

            pirna_str = pirna_url_str % (_APP_LINK_PREFIX, str(pirna), str(pirna))
            results_list.append([pirna_str, target_str, str(len(target_list))])

        context['data'] = results_list
        return render_to_response("irndb2/pathway_pirna.html", context)

    elif url_type == 'mirna':
        if pathwaytype == 'KEGG':
            t2p_list = T2K.objects.filter(kegg = pw_obj).select_related('target').distinct()
        elif pathwaytype == 'REACTOME':
            t2p_list = T2R.objects.filter(path = pw_obj).select_related('target').distinct()
        else:
            t2p_list = T2W.objects.filter(wikipath = pw_obj).select_related('target').distinct()

        # exp miRNA
        t2p_list1 = t2p_list.filter(~Q(mirna_exp = '0')).select_related('target').distinct()
        dict_l2t1 = {}
        for t2p in t2p_list1:
            for mirna in t2p.mirna_exp.split(','):
                dict_l2t1[mirna] = dict_l2t1.get(mirna, []) + [str(t2p.target.symbol)]
                
        results_list1 = []
        for mirna, target_list in dict_l2t1.items():
            target_list = list(set(target_list))
            target_list.sort()
            target_str = ', '.join([target_url_str % (_APP_LINK_PREFIX, str(s), str(s)) for s in target_list])

            mirna_str = mirna_url_str % (_APP_LINK_PREFIX, str(mirna), str(mirna))
            results_list1.append([mirna_str, target_str, str(len(target_list))])
            
        context['data1'] = results_list1
        
        # predicted miRNA
        t2p_list2 = t2p_list.filter(~Q(mirna_pred = '0')).select_related('target').distinct()
        dict_l2t2 = {}
        for t2p in t2p_list2:
            for mirna in t2p.mirna_pred.split(','):
                dict_l2t2[mirna] = dict_l2t2.get(mirna, []) + [str(t2p.target.symbol)]
                
        results_list2 = []
        for mirna, target_list in dict_l2t2.items():
            target_list = list(set(target_list))
            target_list.sort()
            target_str = ', '.join([target_url_str % (_APP_LINK_PREFIX, str(s), str(s)) for s in target_list])

            mirna_str = mirna_url_str % (_APP_LINK_PREFIX, str(mirna), str(mirna))
            results_list2.append([mirna_str, target_str, str(len(target_list))])
            
        context['data2'] = results_list2
        return render_to_response("irndb2/pathway_mirna.html", context)

    else:
        if pathwaytype == 'KEGG':
            t2p_list = T2K.objects.filter(kegg = pw_obj).select_related('target').distinct()
        elif pathwaytype == 'REACTOME':
            t2p_list = T2R.objects.filter(path = pw_obj).select_related('target').distinct()
        else:
            t2p_list = T2W.objects.filter(wikipath = pw_obj).select_related('target').distinct()
            
        target_list = t2p_list.values_list('target')
        num_lncrnas = L2T.objects.filter(target__in = target_list).values('lncrna').distinct().count()
        num_pirnas = P2T.objects.filter(target__in = target_list).values('pirna').distinct().count()
        num_mirnas_exp = M2T_EXP.objects.filter(target__in = target_list).values('mirna').distinct().count()
        num_mirnas_pred = M2T_PRED.objects.filter(target__in = target_list).values('mirna').distinct().count()
        num_targets = len(t2p_list)

        context["target_str"] = '+'.join([str(t2p.target.id) for t2p in t2p_list])
        context['num_lncrnas'] = num_lncrnas
        context['num_pirnas'] = num_pirnas
        context['num_mirnas_exp'] = num_mirnas_exp
        context['num_mirnas_pred'] = num_mirnas_pred
        context['num_targets'] = num_targets
        return render_to_response("irndb2/pathway_base.html", context)


def target_method(request, sym):
    context = {}
    context["entity_type"] = "target"
    a = Target.objects.filter(symbol__regex=r'^%s$'%sym) # exact match, kind of a hack as the __exact did not work
    if a.count() > 1:
        context["error"] = 'Query "%s" resulted in more then 1 entitiy.'%sym
        return render(request, "irndb2/404.html", context)
    elif not a.exists():
        context["error"] = 'Query "%s" resulted in 0 entities.'%sym
        return render(request, "irndb2/404.html", context)
    else:
        target_obj = a[0]
        tid = target_obj.id

    context["t"] = target_obj

    url_type = request.GET.get('type', 'a')
    if url_type not in ["mirna","experiment","pirna","go","lncrna","pathway"]:
        context['m_exp'] = []
        context['m_pred'] = []

        immu_sources = target_obj.immusources.split(',')
        immu_sources.sort()

        # septicshock, MAPK and IRIS do not have seperate resources to link to.
        innatedb_url_template = 'http://innatedb.com/moleculeSearch.do?taxonId=all&field1=name&keyword1=%s'
        immport_url = 'http://immport.org/immport-open/public/reference/genelists'
        immunome_url = 'http://structure.bmc.lu.se/idbase/Immunome/index.php'
        dISources = {'IRIS': innatedb_url_template % target_obj.symbol,
                    'ImmPort': immport_url,
                    'InnateDB': innatedb_url_template % target_obj.symbol ,
                    'MAPK/NFKB': innatedb_url_template % target_obj.symbol,
                    'SepticShock': innatedb_url_template % target_obj.symbol,
                    'Immunome': immunome_url}

        immu_source_template  = '<a class="g" href="%s" title="Link to source database">%s</a>'
        immu_sources_links = []
        for isource in immu_sources:
            immu_sources_links.append(immu_source_template % (dISources[isource], isource))
        immu_sources_links = ', '.join(immu_sources_links)
        
        context["t"].immusourcelinks = immu_sources_links
        return render_to_response("irndb2/target_base.html", context)

    elif url_type == "pirna":
        aQS = P2T.objects.filter(target=target_obj.id).select_related('pirna',
                                                                     'target').values_list('pirna__id',
                                                                                           'pirna__pname',
                                                                                           'pirna__palias',
                                                                                           'pirna__paccession',
                                                                                           'pmid').distinct()
        aRes = []
        for t in aQS:
            a = list(t)

            paccession_link = 'http://www.ncbi.nlm.nih.gov/nuccore/'+'%2C'.join(a[3].split(','))
            a.append(paccession_link)
            a[3] = ', '.join(a[3].split(','))
            #http://www.ncbi.nlm.nih.gov/pubmed/?term=8751592[uid]+OR+16204232[uid]+OR+23931754[uid]
            aPMID = [s.strip() for s in a[4].split(',')]
            sLink = 'http://www.ncbi.nlm.nih.gov/pubmed/?term='
            for i in xrange(len(aPMID)):
                if i+1 < len(aPMID):
                    sLink += '%s[uid]+OR+'%(aPMID[i])
                else:
                    sLink += '%s[uid]'%(aPMID[i]) # last one
            a.append(sLink)
            a[2] = ', '.join(a[2].split(',')) # alias
            a.append('piRBase') # add source
            aRes.append(a)

        #aRes = [ [id, name, alias, accession, pmid, accession_link, sPMIDLink, source] ]
        context['list']  = aRes
        return render_to_response("irndb2/target_pirna.html", context)


    elif url_type == "lncrna":
        aQS = L2T.objects.filter(target=target_obj.id).select_related('lncrna',
                                                                     'target').values_list('lncrna__id',
                                                                                           'lncrna__lsymbol',
                                                                                           'lncrna__lname',
                                                                                           'lncrna__lalias',
                                                                                           'lncrna__llink',
                                                                                           'pmid',
                                                                                           'source').distinct()
        aRes = []
        for t in aQS:
            a = list(t)
            a[3] = ', '.join(a[3].split(','))
            aRes.append(a)

        context['list'] = aRes
        return render_to_response("irndb2/target_lncrna.html", context)

    elif url_type == "mirna":
        aM = M2T_EXP.objects.filter(target=target_obj.id).select_related('mirna',
                                                                         'target').values_list('mirna__id',
                                                                                               'mirna__mname',
                                                                                               'mirna__mirbase_id',
                                                                                               'sources').distinct()
        aMexp = []
        for t in aM:
            a = list(t)
            a[3] = a[3].split(',')
            a[3].sort()
            aMexp.append(a)

        aM = M2T_PRED.objects.filter(target=target_obj.id).select_related('mirna',
                                                                          'target').values_list('mirna__id',
                                                                                                'mirna__mname',
                                                                                                'mirna__mirbase_id',
                                                                                                'sources').distinct()
        aMpred = []
        for t in aM:
            a = list(t)
            a[3] = a[3].split(',')
            a[3].sort()
            aMpred.append(a)

        context['m_exp'] = aMexp
        context['m_pred'] = aMpred
        return render(request, 'irndb2/target_mirna.html', context)

    elif url_type == "pathway":
        aW = T2W.objects.filter(target=target_obj.id).select_related('wikipath').values_list('wikipath__id',
                                                                                             'wikipath__wikipathid',
                                                                                             'wikipath__wikipathname').distinct()
        aK = T2K.objects.filter(target=target_obj.id).select_related('kegg').values_list('kegg__id',
                                                                                        'kegg__keggid',
                                                                                        'kegg__keggname').distinct()
        aR = T2R.objects.filter(target=target_obj.id).select_related('path').values_list('path__id',
                                                                                        'path__pathid',
                                                                                        'path__pathname').distinct()
        aK2 = []
        for t in aK:
            a = list(t)
            a.append(a[1])  # original pathid
            a[1] = a[1].split(':')[1]
            aK2.append(tuple(a))

        context = {'t':target_obj, 'wikipath':aW, 'kegg':aK2, 'reactome':aR}
        return render(request, 'irndb2/target_pathway.html', context)

    elif url_type == "go":
        aG = T2G.objects.filter(target=target_obj.id).select_related('go').values_list('go__id',
                                                                                       'go__goid',
                                                                                       'go__goname',
                                                                                       'go__gocat',
                                                                                       'pmid').distinct()
        aGp = []
        aGf = []
        aTemp = []
        for t in aG:
            aPMID = [str(s).strip() for s in t[4].split(',')]
            if t[3]=='Process':
                aGp.append((t[0], t[1], t[2], aPMID))
            elif t[3]=='Function':
                aGf.append((t[0], t[1], t[2], aPMID))

        context['go_p'] = aGp
        context['go_f'] = aGf
        return render(request, 'irndb2/target_go.html', context)

    elif url_type == 'experiment':
        """"""
        aE = T2C7.objects.filter(target=target_obj.id).select_related('msigdb_c7').values_list('msigdb_c7__geoid',
                                                                                               'msigdb_c7__c7name',
                                                                                               'msigdb_c7__c7expr',
                                                                                               'msigdb_c7__c7url',
                                                                                               'msigdb_c7__c7organism',
                                                                                               'msigdb_c7__c7pmid',
                                                                                               'msigdb_c7__c7author',
                                                                                               'msigdb_c7__c7desc').distinct()
        aExp_up = []
        aExp_dn = []
        for t in aE:
            if t[2] == 'UP':
                aExp_up.append((t[0], t[1], t[3], t[4], t[5], t[6], t[7]))
            elif t[2] == 'DN':
                aExp_dn.append((t[0], t[1], t[3], t[4], t[5], t[6], t[7]))
        context = {'t':target_obj, 'exp_up':aExp_up, 'exp_dn':aExp_dn}
        return render(request, 'irndb2/target_experiments.html', context)


def mirna_method(request, name, flush=False):
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


    target_url = '<a class="t1" title="Link to IRNdb target page" href="%s/target/%s">%s</a>'
    irndb_kegg_url = '<a class="g" title="IRNdb pathway view" href="%s/kegg/%s">%s</a>'
    irndb_wikipath_url = '<a class="g" title="IRNdb pathway view" href="%s/wikipathway/%s">%s</a>'
    kegg_url = '<a class="g" title="Link to KEGG" href="http://www.genome.jp/dbget-bin/www_bget?pathway:%s">%s</a>'
    wikipath_url = '<a class="g" title="Link to Wikipathway" href="http://www.wikipathways.org/instance/%s">%s</a>'
    irndb_reactome_url = '<a class="g" title="IRNdb pathway view" href="%s/reactome/%s">%s</a>'
    reactome_url = '<a class="g" title="Link to REACTOME" href="http://www.reactome.org/PathwayBrowser/#/%s">%s</a>'
    go_url = '<a class="g" title="Link to Gene Ontology" href="http://amigo.geneontology.org/amigo/term/%s">%s</a>'
    ncbi_url = '<a class="t1" title="Link to NCBI gene" href="http://www.ncbi.nlm.nih.gov/gene/%s">%s</a>'

    ## type of context to return
    url_type = request.GET.get('type', 'a')
    if url_type not in ['p','g','r','t', 'e']:
        return render(request, 'irndb2/mirna_base.html', context)
    elif url_type == 'e':
        a_expr = M2EXPR.objects.filter(mirbase_id = mirna_obj.mirbase_id).distinct().order_by('celltype').annotate(exprfreq100=F('exprfreq')*100).values('celltype', 'exprfreq', 'exprfreq100')
        #a_expr = a_expr.reverse()
        context["ct_expr"] = a_expr 
        return render(request, 'irndb2/mirna_celltype.html', context)

    elif url_type=='g':
        ## fetch pathways from session cache if exists or create new
        if 'goprocess' in request.session['mirnas'][mid]:
            aP  = request.session['mirnas'][mid]['goprocess']
            aF  = request.session['mirnas'][mid]['gofunction']
        else:
            aP = []
            aF = []

            aIDs = list(set([a[0] for a in aImmStrictExp+aImmExp+aImm+aImmStrict]))
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
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                goid = str(k[0])
                goname = str(k[1])

                goname_url = go_url % (goid, goname)
                goid_url = go_url % (goid, goid)

                aP.append([ goname_url, goid_url, gene_symbols, str(len(aT))]) 
            aF = []
            for k,v in dGf.items():
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                goid = str(k[0])
                goname = str(k[1])

                goname_url = go_url % (goid, goname)
                goid_url = go_url % (goid, goid)

                aF.append([ goname_url, goid_url, gene_symbols, str(len(aT))]) 


            request.session['mirnas'][mid]['goprocess'] = aP
            request.session['mirnas'][mid]['gofunction'] = aF
            request.session.modified = True

        context['go_p'] = aP
        context['go_f'] = aF
        return render(request, 'irndb2/rna_go.html', context)

    elif url_type=="p":
        ## fetch pathways from session cache if exists or create new
        if 'wikipath' in request.session['mirnas'][mid]:
            aW  = request.session['mirnas'][mid]['wikipath']
            aK  = request.session['mirnas'][mid]['kegg']
            aR  = request.session['mirnas'][mid]['reactome']
        else:
            ## create new
            # target ids
            aIDs = list(set([a[0] for a in aImmStrictExp+aImmExp+aImm+aImmStrict]))
           
            # wikipath exp
            aWtemp = list(T2W.objects.filter(target__in=aIDs).select_related('target', 'wikipath').values_list('wikipath__wikipathid', 'wikipath__wikipathname', 'target__id', 'target__symbol', 'target__tname').distinct())
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                pathid_orig = str(k[0])
                pathname = str(k[1])

                pathname_url = irndb_wikipath_url % (_APP_LINK_PREFIX, pathid_orig, pathname)
                pathid_url = wikipath_url % (pathid_orig, pathid_orig)

                aWtemp.append([ pathname_url, pathid_url, gene_symbols, str(len(aT))]) 
            aW = aWtemp[:]

            aWtemp = list(T2K.objects.filter(target__in=aIDs).select_related('target', 'kegg').values_list('kegg__keggid', 'kegg__keggname', 'target__id', 'target__symbol', 'target__tname').distinct())
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in  aT]))

                pathid_orig = str(k[0])
                pathid = str(k[0].split(':')[1])
                pathname = str(k[1])

                pathname_url = irndb_kegg_url % (_APP_LINK_PREFIX, pathid_orig, pathname)
                pathid_url = kegg_url % (pathid, pathid)

                aWtemp.append([ pathname_url, pathid_url, gene_symbols, str(len(aT))]) 
            aK = aWtemp[:]

            aWtemp = list(T2R.objects.filter(target__in=aIDs).select_related('target', 'path').values_list('path__pathid', 'path__pathname', 'target__id', 'target__symbol', 'target__tname').distinct())
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                pathid_orig = str(k[0])
                pathname = str(k[1])

                pathname_url = irndb_reactome_url % (_APP_LINK_PREFIX, pathid_orig, pathname)
                pathid_url = reactome_url % (pathid_orig, pathid_orig)

                aWtemp.append([ pathname_url, pathid_url, gene_symbols, str(len(aT))]) 
            aR = aWtemp[:]

            ## push to session cash
            request.session['mirnas'][mid]['wikipath'] = aW
            request.session['mirnas'][mid]['kegg'] = aK
            request.session['mirnas'][mid]['reactome'] = aR
            
            request.session.modified = True

        context['wikipath'] = aW
        context['kegg'] = aK
        context['reactome'] = aR
        
        context['type'] = url_type
        return render(request, 'irndb2/rna_pathways.html', context)

    elif url_type == "r":
        if 'tfbs' in request.session['mirnas'][mid]:
            list_res  = request.session['mirnas'][mid]['tfbs']
        else:
            # fetch primary for mirna
            primaries = list(MPRIMARY2MATURE.objects.filter(mature_id=mirna_obj.mirbase_id).values_list('primary','name','chr_str').distinct())
            # Fetch TFBS for primaries
            list_res = []
            for t in primaries:
                list_tfbs = list(MPRIMARY2TFBS.objects.filter(primary=t[0]).values_list('tfbs_symbol', 'tfbs_id', 'chr_str', 'celltype', 'experiment_source','fdr', 'distance_primary').distinct())
                for t2 in list_tfbs:
                    temp = [str(s) for s in list(t) + list(t2)]
                    list_res.append(temp)
            
            # push to cache
            request.session['mirnas'][mid]['tfbs'] = list_res
            request.session.modified = True
            
        context['tfbs_list'] = list_res
        return render(request, 'irndb2/mirna_tfbs.html', context)

    elif url_type == "t": # target view
        # experiemtnal targets
        aTargetsExp = aImmStrictExp + aImmExp
        # predicted mouse targets
        aTargets = aImmStrict + aImm

        ## speed up prepare data for js load
        list_targets_exp = []
        # 'target__id', 'target__symbol','target__tname','target__immusources','target__strict','sources'
        for t in aTargetsExp:
            symbol = str(t[1])
            name = str(t[2])
            geneid = str(t[0])
            symbol_url_str = target_url % (_APP_LINK_PREFIX, symbol, symbol)
            name_url_str = ncbi_url % (geneid, name)
            geneid_url_str = ncbi_url % (geneid, geneid)
            sources = t[3]
            sources.sort()
            immusources = ',<br> '.join([str(s).strip() for s in sources])
            if t[4] == 1:
                species = 'mouse'
            else:
                species = 'human'
            sources = t[5]
            sources.sort()
            targetsource = ',<br> '.join([str(s).strip() for s in sources])
            
            list_targets_exp.append([symbol_url_str, name_url_str, geneid_url_str, species, immusources, targetsource])
        
        list_targets = []
        for t in aTargets:
            symbol = str(t[1])
            name = str(t[2])
            geneid = str(t[0])
            symbol_url_str = target_url % (_APP_LINK_PREFIX, symbol, symbol)
            name_url_str = ncbi_url % (geneid, name)
            geneid_url_str = ncbi_url % (geneid, geneid)
            sources = t[3]
            sources.sort()
            immusources = ',<br> '.join([str(s).strip() for s in sources])
            if t[4] == 1:
                species = 'mouse'
            else:
                species = 'human'
            sources = t[5]
            sources.sort()
            targetsource = ',<br> '.join([str(s).strip() for s in sources])
            
            list_targets.append([symbol_url_str, name_url_str, geneid_url_str, species, immusources, targetsource])
        
        context['targets_imm'] = list_targets
        context['targets_imm_exp'] = list_targets_exp
        context['enrichr_exp'] = '\\n'.join([t[1] for t in aTargetsExp])
        context['enrichr_pred'] = '\\n'.join([t[1] for t in aTargets])
        context['bM'] = bM
        context['type'] = url_type

        return render(request, 'irndb2/mirna_targets.html', context)


def lncrna_method(request, sym, flush=False): # need to change to False for prod.
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

    target_url = '<a class="t1" title="Link to IRNdb target page" href="%s/target/%s">%s</a>'
    irndb_kegg_url = '<a class="g" title="IRNdb pathway view" href="%s/kegg/%s">%s</a>'
    irndb_wikipath_url = '<a class="g" title="IRNdb pathway view" href="%s/wikipathway/%s">%s</a>'
    kegg_url = '<a class="g" title="Link to KEGG" href="http://www.genome.jp/dbget-bin/www_bget?pathway:%s">%s</a>'
    irndb_reactome_url = '<a class="g" title="IRNdb pathway view" href="%s/reactome/%s">%s</a>'
    reactome_url = '<a class="g" title="Link to REACTOME" href="http://www.reactome.org/PathwayBrowser/#/%s">%s</a>'
    wikipath_url = '<a class="g" title="Link to Wikipathway" href="http://www.wikipathways.org/instance/%s">%s</a>'
    go_url = '<a class="g" title="Link to Gene Ontology" href="http://amigo.geneontology.org/amigo/term/%s">%s</a>'
    pmid_url = '<a class="g" title="Link to NCBI" href="https://www.ncbi.nlm.nih.gov/pubmed/%s">%s</a>'
    ncbi_url = '<a class="t1" title="Link to NCBI gene" href="http://www.ncbi.nlm.nih.gov/gene/%s">%s</a>'
    
    # fetch type via GET method
    url_type = request.GET.get('type', 'x') # some char not in use
    if url_type not in ["p","g","t"]: # add possible tabs here
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
            #t[6] = ', '.join(t[6].split(','))
        aTargets = aTargetsFinal

        request.session['lncrnas'][lid] = {'targets':aTargets}
        request.session.modified = True

    #-- target tab --
    if url_type == "t":
        list_targets = []
        for t in aTargets:
            symbol = str(t[1])
            name = str(t[2])
            geneid = str(t[0])
            symbol_url_str = target_url % (_APP_LINK_PREFIX, symbol, symbol)
            name_url_str = ncbi_url % (geneid, name)
            sources = t[4]
            sources.sort()
            immusources = ',<br>'.join([str(s).strip() for s in sources])
            if t[3] == 1:
                species = 'mouse'
            else:
                species = 'human'
            sources = [str(s).strip() for s in t[6].split(',')]
            sources.sort()
            targetsource = ',<br>'.join([str(s).strip() for s in sources])


            pmid_list = [str(s).strip() for s in t[5].split(',')]
            pmid_url_str = ',<br>'.join([pmid_url % (s,s) for s in pmid_list])
            
            list_targets.append([symbol_url_str, name_url_str, species, immusources, targetsource, pmid_url_str])
        
        context['l'] = lncrna_obj
        context['targets'] = list_targets
        context['enrichr'] = '\\n'.join([t[1] for t in aTargets])
        context['enrichr_name'] = lncrna_obj.lsymbol
        context['bL'] = bL
        context['existed'] = iExisted
        return render(request, 'irndb2/rna_targets.html', context)

    #-- GO tab --
    if url_type == 'g':
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
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                goid = str(k[0])
                goname = str(k[1])

                goname_url = go_url % (goid, goname)
                goid_url = go_url % (goid, goid)

                aP.append([ goname_url, goid_url, gene_symbols, str(len(aT))]) 
               
            aF = []
            for k,v in dGf.items():
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                goid = str(k[0])
                goname = str(k[1])

                goname_url = go_url % (goid, goname)
                goid_url = go_url % (goid, goid)

                aF.append([ goname_url, goid_url, gene_symbols, str(len(aT))])

            request.session['lncrnas'][lid]['goprocess'] = aP
            request.session['lncrnas'][lid]['gofunction'] = aF
            request.session.modified = True

        context['go_p'] = aP
        context['go_f'] = aF
        context['existed'] = iGexisted
        return render(request, 'irndb2/rna_go.html', context)

    #-- pathway tab --
    elif url_type=="p":
        ## fetch pathways from session cache if exists or create new
        if 'wikipath' in request.session['lncrnas'][lid]:
            aW  = request.session['lncrnas'][lid]['wikipath']
            aK  = request.session['lncrnas'][lid]['kegg']
            aR  = request.session['lncrnas'][lid]['reactome']
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
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                pathid_orig = str(k[0])
                pathname = str(k[1])

                pathname_url = irndb_wikipath_url % (_APP_LINK_PREFIX, pathid_orig, pathname)
                pathid_url = wikipath_url % (pathid_orig, pathid_orig)

                aWtemp.append([ pathname_url, pathid_url, gene_symbols, str(len(aT))]) 
            aW = aWtemp[:]

            # KEGG
            aWtemp = T2K.objects.filter(target__in=aIDs).select_related('target', 'kegg').values_list('kegg__keggid', 'kegg__keggname', 'target__id', 'target__symbol', 'target__tname').distinct()
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in  aT]))

                pathid_orig = str(k[0])
                pathid = str(k[0].split(':')[1])
                pathname = str(k[1])

                pathname_url = irndb_kegg_url % (_APP_LINK_PREFIX, pathid_orig, pathname)
                pathid_url = kegg_url % (pathid, pathid)

                aWtemp.append([ pathname_url, pathid_url, gene_symbols, str(len(aT))]) 
                
            aK = aWtemp[:]

            # Reactome
            aWtemp = list(T2R.objects.filter(target__in=aIDs).select_related('target', 'path').values_list('path__pathid', 'path__pathname', 'target__id', 'target__symbol', 'target__tname').distinct())
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                pathid_orig = str(k[0])
                pathname = str(k[1])

                pathname_url = irndb_reactome_url % (_APP_LINK_PREFIX, pathid_orig, pathname)
                pathid_url = reactome_url % (pathid_orig, pathid_orig)

                aWtemp.append([ pathname_url, pathid_url, gene_symbols, str(len(aT))]) 
            aR = aWtemp[:]
            
            ## puch to session cash
            request.session['lncrnas'][lid]['wikipath'] = aW
            request.session['lncrnas'][lid]['kegg'] = aK
            request.session['lncrnas'][lid]['reactome'] = aK
            request.session.modified = True

        context['wikipath'] = aW
        context['kegg'] = aK
        context['reactome'] = aR
        context['type'] = url_type
        return render(request, 'irndb2/rna_pathways.html', context)


def pirna_method(request, name, flush=False): # need to change to False for prod.
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
    pirna_obj.ppmid_link = 'http://www.ncbi.nlm.nih.gov/pubmed/' + ','.join(aPMID)
    
    pirna_obj.ppmid = ', '.join(pirna_obj.ppmid.split(','))
    pirna_obj.palias = ', '.join(pirna_obj.palias.split(','))
    # currently only one source
    ## TODO: Needs changes in db structure to dad more sources
    pirna_obj.psource = 'piRBase'

    # fetch type via GET method
    url_type = request.GET.get('type', 'x') # some char not in use
    if url_type not in ["p","g","t"]: # add possible tabs here
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


    target_url = '<a class="t1" title="Link to IRNdb target page" href="%s/target/%s">%s</a>'
    irndb_kegg_url = '<a class="g" title="IRNdb pathway view" href="%s/kegg/%s">%s</a>'
    irndb_wikipath_url = '<a class="g" title="IRNdb pathway view" href="%s/wikipathway/%s">%s</a>'
    kegg_url = '<a class="g" title="Link to KEGG" href="http://www.genome.jp/dbget-bin/www_bget?pathway:%s">%s</a>'
    wikipath_url = '<a class="g" title="Link to Wikipathway" href="http://www.wikipathways.org/instance/%s">%s</a>'
    go_url = '<a class="g" title="Link to Gene Ontology" href="http://amigo.geneontology.org/amigo/term/%s">%s</a>'
    ncbi_url = '<a class="t1" title="Link to NCBI gene" href="http://www.ncbi.nlm.nih.gov/gene/%s">%s</a>'
    pmid_url = '<a class="g" title="Link to NCBI" href="https://www.ncbi.nlm.nih.gov/pubmed/%s">%s</a>'
    irndb_reactome_url = '<a class="g" title="IRNdb pathway view" href="%s/reactome/%s">%s</a>'
    reactome_url = '<a class="g" title="Link to REACTOME" href="http://www.reactome.org/PathwayBrowser/#/%s">%s</a>'
    
    #-- target tab --
    if url_type == "t":
        list_targets = []
        for t in aTargets:
            symbol = str(t[1])
            name = str(t[2])
            geneid = str(t[0])
            symbol_url_str = target_url % (_APP_LINK_PREFIX, symbol, symbol)
            name_url_str = ncbi_url % (geneid, name)
            sources = t[4]
            sources.sort()
            immusources = ',<br>'.join([str(s).strip() for s in sources])
            if t[3] == 1:
                species = 'mouse'
            else:
                species = 'human'
            pmid_list = [str(s).strip() for s in t[5].split(',')]
            pmid_url_str = ',<br>'.join([pmid_url % (s,s) for s in pmid_list])
            
            list_targets.append([symbol_url_str, name_url_str, species, immusources, 'piRBase', pmid_url_str])

        
        context['p'] = pirna_obj
        context['targets'] = list_targets
        context['enrichr'] = '\\n'.join([t[1] for t in aTargets])
        context['enrichr_name'] = pirna_obj.pname
        context['bL'] = bL
        context['existed'] = iExisted
        return render(request, 'irndb2/rna_targets.html', context)

    #-- GO tab --
    if url_type == 'g':
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
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                goid = str(k[0])
                goname = str(k[1])

                goname_url = go_url % (goid, goname)
                goid_url = go_url % (goid, goid)

                aP.append([ goname_url, goid_url, gene_symbols, str(len(aT))])
                
            aF = []
            for k,v in dGf.items():
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                goid = str(k[0])
                goname = str(k[1])

                goname_url = go_url % (goid, goname)
                goid_url = go_url % (goid, goid)

                aF.append([ goname_url, goid_url, gene_symbols, str(len(aT))]) 


            request.session['pirnas'][pid]['goprocess'] = aP
            request.session['pirnas'][pid]['gofunction'] = aF
            request.session.modified = True

        context['go_p'] = aP
        context['go_f'] = aF
        context['existed'] = iGexisted
        return render(request, 'irndb2/rna_go.html', context)

    #-- pathway tab --
    elif url_type=="p":
        ## fetch pathways from session cache if exists or create new
        if 'wikipath' in request.session['pirnas'][pid]:
            aW  = request.session['pirnas'][pid]['wikipath']
            aK  = request.session['pirnas'][pid]['kegg']
            aR = request.session['pirnas'][pid]['reactome']
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
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                pathid_orig = str(k[0])
                pathname = str(k[1])

                pathname_url = irndb_wikipath_url % (_APP_LINK_PREFIX, pathid_orig, pathname)
                pathid_url = wikipath_url % (pathid_orig, pathid_orig)

                aWtemp.append([ pathname_url, pathid_url, gene_symbols, str(len(aT))]) 
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
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in  aT]))

                pathid_orig = str(k[0])
                pathid = str(k[0].split(':')[1])
                pathname = str(k[1])

                pathname_url = irndb_kegg_url % (_APP_LINK_PREFIX, pathid_orig, pathname)
                pathid_url = kegg_url % (pathid, pathid)

                aWtemp.append([ pathname_url, pathid_url, gene_symbols, str(len(aT))]) 
            aK = aWtemp[:]

            # Reactome
            aWtemp = list(T2R.objects.filter(target__in=aIDs).select_related('target', 'path').values_list('path__pathid', 'path__pathname', 'target__id', 'target__symbol', 'target__tname').distinct())
            dW = {}
            for tRes in aWtemp:
                tW = (tRes[0], tRes[1])
                if tW not in dW:
                    dW[tW] = set()
                dW[tW].add((tRes[3], tRes[2], tRes[4]))
            aWtemp = []
            for k,v in dW.items():
                aT = list([str(t[0]) for t in v])
                aT.sort()
                gene_symbols = str(', '.join([target_url %(_APP_LINK_PREFIX, gene, gene) for gene in aT]))

                pathid_orig = str(k[0])
                pathname = str(k[1])

                pathname_url = irndb_reactome_url % (_APP_LINK_PREFIX, pathid_orig, pathname)
                pathid_url = reactome_url % (pathid_orig, pathid_orig)

                aWtemp.append([ pathname_url, pathid_url, gene_symbols, str(len(aT))]) 
            aR = aWtemp[:]

            
            ## puch to session cash
            request.session['pirnas'][pid]['wikipath'] = aW
            request.session['pirnas'][pid]['kegg'] = aK
            request.session['pirnas'][pid]['reactome'] = aR
            request.session.modified = True

        context['wikipath'] = aW
        context['kegg'] = aK
        context['reactome'] = aR
        context['type'] = url_type
        context['existed'] = iPexisted
        return render(request, 'irndb2/rna_pathways.html', context)

    
def search_method(request):
    context = {}
    if request.method == 'GET':
        content = request.GET.get('content', '0')
        query = request.GET.get('q', None)
        query = query.strip()
        
        if content == '0': # go here in any case if content == 0
            context["search_term"] = '+'.join([s.strip() for s in query.split(' ')])  # make urlsafe
            return render(request, "irndb2/search_base.html", context)
       
        elif content == '1' and query:
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

            # pathways
            ## res_reactome = Reactome.objects.filter( Q(pathname__icontains=query) | Q(pathid__icontains=query) ).distinct()
            ## res_wikipath = Wikipath.objects.filter( Q(wikipathname__icontains=query) | Q(wikipathid__icontains=query) ).distinct()
            ## res_kegg = Kegg.objects.filter( Q(keggname__icontains=query) | Q(keggid__icontains=query) ).distinct()
            ## a1 = [[str(t[0]), str(t[1]), 'REACTOME'] for t in res_reactome.values_list('pathid','pathname')]
            ## a2 = [[str(t[0]), str(t[1]), 'WIKIPATHWAY'] for t in res_wikipath.values_list('wikipathid','wikipathname')]
            ## a3 = [[str(t[0]), str(t[1]), 'KEGG'] for t in res_kegg.values_list('keggid','keggname')]
            ## res_path = a1 + a2 + a3
            
            context["search_target"] = res_target
            context["search_mirna"] = res_mirna
            context["search_lncrna"] = res_lncrna
            context["search_pirna"] = res_pirna
            ## context["search_path"] = res_path
            
            search_results_num = 0
            cat_num = 0
            ## for res in [res_target, res_mirna, res_lncrna, res_pirna, res_path]:
            for res in [res_target, res_mirna, res_lncrna, res_pirna]:
                try:
                    len_res = res.count()
                except:
                    len_res = len(res)
                if len_res > 0:
                    cat_num += 1
                search_results_num += len_res

            context["search_results"] = search_results_num
            context["search_cat"] = cat_num
            
        else:
            context["search_term"] = ""
            context["search_results"] = 0
            
        return render(request, 'irndb2/search.html', context)
    # if not GET method return homepage
    else:
        return render(request, "irndb2/home.html", context)


def home_method(request):
    context = {}
    content = request.GET.get('content', '0')
    if content == '0':
        return render(request, "irndb2/home_base.html", context)
    elif content =='1':
        context['num_target'] = Target.objects.all().count()
        context['num_mirna'] = Mirna.objects.all().count()
        context['num_lncrna'] = Lncrna.objects.all().count()
        context['num_pirna'] = Pirna.objects.all().count()
        return render(request, "irndb2/home.html", context)
    else:
        context["error"] = 'Wrong GET parameter.'
        return render(request, "irndb2/404.html", context)


def doc_method(request):
    context = {}
    tab = request.GET.get('tab', 'x')
    context = {}
    if tab not in ['1','2','3','4','5']:
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
    elif tab == '5':
        return render(request, "irndb2/doc_contact.html", context)
    elif tab == 'x':
        return render(request, "irndb2/doc.html", context)
    else:
        context["error"] = 'Wrong tab number for documentation.'
        return render(request, "irndb2/404.html", context)
    
def browse_method(request):
    # get url params
    # can be: rn, celltype, pathways, gene
    type = request.GET.get('type', '0')
    # can be: "mirna", "lncrna", "pirna", "target", "0"
    entitytype = request.GET.get('etype', '0')
    # can be:
    pathwaytype = request.GET.get('pwt', 'x')
    # can be: 0, 1
    dnl = request.GET.get('dnl', '0')
    filename = request.GET.get('f','data.csv')
    content = request.GET.get('content', '0')
    
    context = {}
    context["type"] = type
    context["entity_type"] = entitytype
    context["pwt"] = pathwaytype

    # catch some URL errors early ------
    if entitytype not in ["mirna", "lncrna", "pirna", "target", "0"]:
        context["error"] = 'Wrong URL: etype needs to be one of: mirna, lncrna, pirna, target.'
        return render(request, "irndb2/404.html", context)

    if type == "celltype":
        if entitytype != 'mirna':
            context["error"] = 'Wrong URL: Cell-types currently only available for miRNAs.'
            return render(request, "irndb2/404.html", context)

    elif type == "rna":
        if entitytype not in ["mirna" , "pirna", "lncrna"]:
            context["error"] = 'Wrong URL. etype needs to be one of: mirna, lncrna, pirna for type=rna'
            return render(request, "irndb2/404.html", context)
    elif type == "gene":
        if entitytype != 'target':
            context["error"] = 'Wrong URL. etype needs to be "target" for type=gene.'
            return render(request, "irndb2/404.html", context)
    elif type == "pathway":
        if entitytype not in ["mirna" , "pirna", "lncrna"]:
            context["error"] = 'Wrong URL. etype needs to be one of: mirna, lncrna, pirna for type=pathway'
            return render(request, "irndb2/404.html", context)
    #-----------------------------------

    if content == '0' and type in ['gene', 'rna', 'celltype']:
        if entitytype == 'target':
            context['title'] = 'Targets'
        elif entitytype == 'lncrna' and type=='rna':
            context['title'] = 'lncRNAs'
        elif entitytype == 'pirna' and type=='rna':
            context['title'] = 'piRNAs'
        elif entitytype == 'mirna' and type=='rna':
            context['title'] = 'miRNAs'
        elif type == 'celltype':
            context['title'] = 'Cell-types'
        return render(request, "irndb2/browse_base.html", context)
    
    
    if entitytype == 'mirna':
        context["rna_title"] = "miRNA"

        # download instead of display
        if dnl == '1' and type != 'pathway' and type != 'celltype':  
            query_set = Mirna.objects.filter(num_immune__gt=0).distinct()
            data = create_data_mirna(query_set, 0)
            response = create_dnl_response(filename, data, ['Name','ID','NumExperimentalMouseImmuneTargets','NumPredictedMouseImmuneTargets','NumExperimentalHumanInferredImmuneTargets','NumPredictedHumanInferredImmuneTargets'])
            return response
        
        # browse pathways instead --> return pathway list
        elif type == 'pathway':
            if pathwaytype not in ["wikipathway","kegg","reactome"]:
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
                    
        elif type == 'celltype':
            list_mirna = [str(t[0]) for t in M2EXPR.objects.all().values_list('mirbase_id').distinct()]
            list_mirnaobj = Mirna.objects.filter(mirbase_id__in = list_mirna).distinct()
            dict_mirna = {}
            for obj in list_mirnaobj:
                dict_mirna[obj.mirbase_id] = obj.mname
            list_ct = M2EXPR.objects.all().order_by('exprfreq')
            list_ct = list_ct.reverse()

            dict_ct = {}
            mirna_url_str = '<a class="m1" href="%s/mirna/%s" title="IRN miRNA details"><span style="white-space: nowrap;">%s (%.2f)</span></a>'
            for obj_m2expr in list_ct:
                try:
                    mirna_name = dict_mirna[obj_m2expr.mirbase_id] 
                except:
                    continue
                exprfreq = float(obj_m2expr.exprfreq) * 100
                dict_ct[obj_m2expr.celltype] = dict_ct.get(obj_m2expr.celltype, []) + [(mirna_name, exprfreq)]

            data = []
            for k,v in dict_ct.items():

                # Sub table
                str_temp = '<table>'
                i = 0
                for mirna in v:
                    if i == 0:
                        str_temp += '<tr>'
                    str_temp += '<td style="padding:0 10px 0 10px;">%s</td>' % (mirna_url_str % (_APP_LINK_PREFIX, mirna[0], mirna[0], mirna[1]))
                    i+=1
                    if i == 3:
                        i = 0
                        str_temp += '</tr>'

                if len(v) % 3 == 0:
                    str_temp += '</table>'
                else:
                    str_temp += '</tr></table>'
                mirna_str = str_temp
                
                # no table just concat with comma
                #mirna_str = ', '.join([mirna_url_str % (_APP_LINK_PREFIX, mirna[0], mirna[0], mirna[1]) for mirna in v])
                data.append([str(k), str(mirna_str), '%i' % (len(v))])

            
                
            context["data"] = data
            return render(request, "irndb2/browse_celltype.html", context)

        # no download --> browse mirnas
        else:  
            query_set = Mirna.objects.filter(num_immune__gt=0).distinct()
            context['data'] = create_data_mirna(query_set, 1)
            return render(request, "irndb2/browse_mirna.html", context)
    
    elif entitytype == 'target':
        if dnl == '1' and type != 'pathway':  # download instead of display
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
        if dnl == '1' and type != 'pathway':  # download instead of display
            query_set = Lncrna.objects.all().distinct()
            data = create_data_lncrna(query_set, 0)
            response = create_dnl_response(filename, data, ['symbol', 'name', 'alias',  'NumMouseInferredImmuneTargets', 'NumHumanInferredImmuneTargets'])
            return response
        
        # browse pathways instead --> return pathway list
        elif type == 'pathway':
            if pathwaytype not in ["wikipathway","kegg","reactome"]:
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
        if dnl == '1' and type != 'pathway':  # download instead of display
            query_set = Pirna.objects.all().distinct()
            data = create_data_pirna(query_set, 0)
            response = create_dnl_response(filename, data, ['name', 'alias', 'accession',  'NumMouseInferredImmuneTargets',
             'NumHumanInferredImmuneTargets'])
            return response
        
        # browse pathways instead --> return pathway list
        elif type == 'pathway':
            if pathwaytype not in ["wikipathway","kegg","reactome"]:
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
        context["error"] = 'Wrong URL.'
        return render(request, "irndb2/404.html", context)

    
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
    rnalink_template = '<a class="m1" href="%s/%s/%s"><span style="white-space: nowrap;">%s</span></a>' # _APP_LINK_PREFIX, rnatype, rnasymbol/name, symbol/name
    pwlink_template = '<a title="Open in IRNdb" class="g" href="%s/%s/%s">%s</a>' # _APP_LINK_PREFIX, pathwaytype, pwid, pwname
    targetlink_template = '<a title="Open in IRNdb" class="t1" href="%s/target/%s"><span style="white-space: nowrap;"> %s </span></a>' # _APP_LINK_PREFIX, symbol, symbol 
  
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
                    rnas = ', '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.pirna.split(',')])
                elif entitytype == 'lncrna':
                    rnas = ', '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.lncrna.split(',')])
                elif entitytype == 'mirna':
                    rnas = ', '.join([str(rnalink_template % (_APP_LINK_PREFIX,
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
                str_table = '<table width="100%"><tbody>'
                row_str = '<tr><td style="width:120px; vertical-align: top; padding-bottom: 10px;">%s</td><td style="padding-bottom: 10px;">%s</td></tr>' % (targetlist[0][0], targetlist[0][1])
                str_table += row_str
                for i in range(1,len(targetlist)):
                    row_str = '<tr style="border-top:1pt solid #f2f2f3;"><td style="width:120px; vertical-align: top; padding-bottom: 10px;">%s</td><td style="padding-bottom: 10px;">%s</td></tr>' % (targetlist[i][0], targetlist[i][1])
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
                    rnas = ', '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.pirna.split(',')])
                elif entitytype == 'lncrna':
                    rnas = ', '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.lncrna.split(',')])
                elif entitytype == 'mirna':
                    rnas = ', '.join([str(rnalink_template % (_APP_LINK_PREFIX,
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
                str_table = '<table width="100%"><tbody>'
                row_str = '<tr><td style="width:120px; vertical-align: top; padding-bottom: 10px;">%s</td><td style="padding-bottom: 10px;">%s</td></tr>' % (targetlist[0][0], targetlist[0][1])
                str_table += row_str
                for i in range(1,len(targetlist)):
                    row_str = '<tr style="border-top:1pt solid #f2f2f3;"><td style="width:120px; vertical-align: top; padding-bottom: 10px;">%s</td><td style="padding-bottom: 10px;">%s</td></tr>' % (targetlist[i][0], targetlist[i][1])
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
                    
    elif pathwaytype == 'reactome':
        if entitytype == 'pirna':
            t2pw_list = T2R.objects.filter(~Q(pirna = '0')).select_related('target', 'path').distinct()
        elif entitytype == 'lncrna':
            t2pw_list = T2R.objects.filter(~Q(lncrna = '0')).select_related('target', 'path').distinct()
        elif entitytype == 'mirna':
            t2pw_list = T2R.objects.filter(~Q(mirna_exp = '0')).select_related('target', 'path').distinct()

        for t2pw in t2pw_list:
            if t2pw.path not in dPW:
                dPW[t2pw.path] = []

            if dnl != '1':
                if entitytype == 'pirna':
                    rnas = ', '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.pirna.split(',')])
                elif entitytype == 'lncrna':
                    rnas = ', '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.lncrna.split(',')])
                elif entitytype == 'mirna':
                    rnas = ', '.join([str(rnalink_template % (_APP_LINK_PREFIX,
                                                              entitytype,
                                                              rna.strip(),
                                                              rna.strip())) for rna in t2pw.mirna_exp.split(',')])


                dPW[t2pw.path].append([ str(targetlink_template % (_APP_LINK_PREFIX,
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

                dPW[t2pw.path].append([ str(t2pw.target.symbol), rnas])

        for wp, targetlist in dPW.items():
            if dnl != '1':
                targetlist.sort()
                str_table = '<table width="100%"><tbody>'
                row_str = '<tr><td style="width:120px; vertical-align: top; padding-bottom: 10px;">%s</td><td style="padding-bottom: 10px;">%s</td></tr>' % (targetlist[0][0], targetlist[0][1])
                str_table += row_str
                for i in range(1,len(targetlist)):
                    row_str = '<tr style="border-top:1pt solid #f2f2f3;"><td style="width:120px; vertical-align: top; padding-bottom: 10px;">%s</td><td style="padding-bottom: 10px;">%s</td></tr>' % (targetlist[i][0], targetlist[i][1])
                    str_table += row_str
                str_table += '</tbody></table>'
                res_list.append([str(pwlink_template % (_APP_LINK_PREFIX,
                                                        pathwaytype,
                                                        str(wp.pathid),
                                                        str(wp.pathname))), str_table])
            else:
                # here make one row per target
                for tlist in targetlist:
                    res_list.append([ str(wp.pathid), str(wp.pathname), tlist[0], tlist[1]])
    return res_list
