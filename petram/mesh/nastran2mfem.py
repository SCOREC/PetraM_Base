
'''
    read .nas file and make MFEM mesh file

    note: it reads only minimum set of grid data

    supported card
        GRID
        CTETRA
        CHEXA
        CTRIA6
        CTRIA3
        CQUAD8
        PSOLID
        PSHELL

    index in nas starts from 1. 
    index in mfem starts from 0.
'''
import numpy as np
import re

fwidth = 16
class NASReader(object):
    def __init__(self, filename):
        self.filename = filename
        self.dataset = None
    def load(self):
        # check format length
        num_lines = sum(1 for line in open(self.filename))
        num_lines_base = num_lines/100
        fid = open(self.filename, 'r')
        while True:
            l = fid.readline()
            if l.startswith('+CONT'):
                globals()['fwidth'] = 8
                print('short format ' + str(num_lines) + ' lines')
                break
            elif l.startswith('*CONT'):
                globals()['fwidth'] = 16
                print('long format ' + str(num_lines) + ' lines')
                break                
        fid.close()
        
        fid = open(self.filename, 'r')
        while True:
            l = fid.readline()
            if l.startswith('$ Grid data section'): break

        num_grid = 0
        while True:
            l = fid.readline()            
            if l.startswith('GRID'):num_grid = num_grid + 1
            if l.startswith('$ Element data section'):break
        fid.close()
        fid = open(self.filename, 'r')
        cl = ''

        while True:
            l = self._read_line(fid)
            if l.startswith('$ Grid data section'): break

        grids = [None]*num_grid  ### reading grid      
        for i in range(num_grid):
            l = self._read_line(fid)
            if l.startswith('$ Element data section'):break
            g = self.parse_grid_fixed(l)
            grids[i] = np.array((float(g[3]), float(g[4]), float(g[5])))
        grids = np.vstack(grids)

        elems = {'TRIA6':[],
                 'TRIA3':[],
                 'TETRA':[],
                 'HEXA':[],
                 'QUAD4':[],
                 'QUAD8':[]} ### reading elements
        print("reading elements")
        ll = 0
        while True:            
            l = self._read_line(fid)
            if l.startswith('$ Property data section'):break
            if l.startswith('CTRIA6'):
                elems['TRIA6'].append(self.parse_tria6_fixed(l))
            elif l.startswith('CTRIA3'):
                elems['TRIA3'].append(self.parse_tria3_fixed(l))
            elif l.startswith('CTETRA'):
                elems['TETRA'].append(self.parse_tetra_fixed(l))
            elif l.startswith('CHEXA'):
                elems['HEXA'].append(self.parse_hexa_fixed(l))
            elif l.startswith('CQUAD8'):
                elems['QUAD8'].append(self.parse_quad8_fixed(l))
            elif l.startswith('CQUAD4'):
                elems['QUAD4'].append(self.parse_quad4_fixed(l))
            else: 
                print("Element not supported: " + l)
                continue
            ll += 1
            if ll % num_lines_base == 0:
               print(str(ll/num_lines_base) + "% done.(" + str(ll) + ")")
        print("reading elements   (done)")
        new_elems = {}
        if len(elems['TETRA']) > 0:
            TETRA = np.vstack([np.array((int(g[3]), int(g[4]), int(g[5]), int(g[6]),))
                           for g in elems['TETRA']])
            TETRA_ATTR = np.array([int(g[2]) for g in elems['TETRA']]) #PSOLID ID
            idx = [len(np.unique(x)) == 4 for x in TETRA]
            if not all(idx):
                print("some TETRA has no volume")
                TETRA = TETRA[idx, :]
                TETRA_ATTR = TETRA_ATTR[idx]
                
            new_elems['TETRA'] = TETRA-1
            new_elems['TETRA_ATTR'] = TETRA_ATTR
            
        if len(elems['TRIA6']) > 0:
            TRIA6 = np.vstack([np.array((int(g[3]), int(g[4]), int(g[5]), ))
                               for g in elems['TRIA6']])
            TRIA6_ATTR = np.array([int(g[2]) for g in elems['TRIA6']])

            idx = [len(np.unique(x)) == 3 for x in TRIA6]
            if not all(idx):
                print("some TRIA6 has no area")
                TRIA6 = TRIA6[idx, :]
                TRIA6_ATTR = TRIA6_ATTR[idx]
                

            idx = [np.any([len(np.intersect1d(x, y))==3 for y in TETRA]) for x in TRIA6]
            if not all(idx):
                print("some TRIA6 is not surface of TETRA!")
                TRIA6 = TRIA6[idx, :]
                TRIA6_ATTR = TRIA6_ATTR[idx]

            new_elems['TRIA6'] = TRIA6-1
            new_elems['TRIA6_ATTR'] = TRIA6_ATTR

        if len(elems['TRIA3']) > 0:                          
            TRIA3 = np.vstack([np.array((int(g[3]), int(g[4]), int(g[5]), ))
                           for g in elems['TRIA3']])
            TRIA3_ATTR = np.array([int(g[2]) for g in elems['TRIA3']])  #PSHELL ID
            new_elems['TRIA3'] = TRIA3-1
            new_elems['TRIA3_ATTR'] = TRIA3_ATTR
            
        if len(elems['HEXA']) > 0:                                  
            HEXA = np.vstack([np.array((int(g[3]), int(g[4]), int(g[5]), int(g[6]),
                           int(g[7]), int(g[8]), int(g[9]), int(g[10]),))
                           for g in elems['HEXA']])
            HEXA_ATTR = np.array([int(g[2]) for g in elems['HEXA']]) #PSOLID ID
            new_elems['HEXA'] = HEXA-1
            new_elems['HEXA_ATTR'] = HEXA_ATTR

        if len(elems['QUAD8']) > 0:
            QUAD8 = np.vstack([np.array((int(g[3]), int(g[4]), int(g[5]), int(g[6])))
                           for g in elems['QUAD8']])
            QUAD8_ATTR = np.array([int(g[2]) for g in elems['QUAD8']])  #PSHELL ID
            new_elems['QUAD8'] = QUAD8-1
            new_elems['QUAD8_ATTR'] = QUAD8_ATTR
            
        if len(elems['QUAD4']) > 0:
            QUAD4 = np.vstack([np.array((int(g[3]), int(g[4]), int(g[5]), int(g[6])))
                           for g in elems['QUAD4']])
            QUAD4_ATTR = np.array([int(g[2]) for g in elems['QUAD4']])  #PSHELL ID
            new_elems['QUAD4'] = QUAD4-1
            new_elems['QUAD4_ATTR'] = QUAD4_ATTR

        elems =  new_elems

        props = {'PSOLID':[],
                 'PSHELL':[]}
        print("reading shell/solid")
        while True:            
            l = self._read_line(fid)
            if l.startswith('ENDDATA'):break
            if l.startswith('PSOLID'):
                props['PSOLID'].append(self.parse_psolid_fixed(l))
            elif l.startswith('PSHELL'):
                props['PSHELL'].append(self.parse_pshell_fixed(l))
            else: pass
            ll += 1
            if ll % num_lines_base == 0:
               print(str(ll/num_lines_base) + "% done.")
        print("reading shell/solid ...(done)")                          
        PSHELL = np.array([int(g[1]) for g in props['PSHELL']])  #PSHELL
        PSOLID = np.array([int(g[1]) for g in props['PSOLID']])  #PSOLID

        props = {'PSOLID': PSOLID, 
                 'PSHELL': PSHELL }


        dataset = {'PROPS':props,
                   'ELEMS' :elems,
                   'GRIDS':grids}
        fid.close()
        self.dataset = dataset

    def plot_tet(self, idx, **kwargs):
        from ifigure.interactive import solid
        
        grids = self.dataset['GRIDS']
        tet = self.dataset['ELEMS']['TETRA']
        i = tet[idx]
        pts = [grids[[i[0], i[1], i[2]]],
               grids[[i[1], i[2], i[3]]],
               grids[[i[2], i[3], i[0]]],
               grids[[i[3], i[0], i[1]]]]
        pts = np.rollaxis(np.dstack(pts), 2, 0)
        solid(pts, **kwargs)
        
    def _read_line(self, fid):
        cl = ''
        while True:
            line =  fid.readline()
            l = line.rstrip("\r\n")
            if (l.startswith('+CONT') or 
                l.startswith('*CONT')): l = cl + l[8:]
            if (l.strip().endswith('+CONT') or
                l.strip().endswith('*CONT')):
                cl = l.strip()[:-5]
                continue
            break
        return l
                
    def parse_grid_fixed(self, l):
        d=fwidth
        if fwidth == 16: l = ' '*8+l        
#        cards= [l[d*i:d*(i+1)].strip() for i in range(8)]
        cards = re.findall('.'*d, l)
        return cards
    def parse_tetra_fixed(self, l):
        d=8              
#        cards= [l[d*i:d*(i+1)].strip() for i in range(13)]
        cards = re.findall('.'*d, l)
        return cards
    def parse_tria6_fixed(self, l):
        d=8
#        cards= [l[d*i:d*(i+1)].strip() for i in range(9)]
        cards = re.findall('.'*d, l)
        return cards
    def parse_tria3_fixed(self, l):
        d=8                
#        cards= [l[d*i:d*(i+1)].strip() for i in range(9)]
        cards = re.findall('.'*d, l)
        return cards
    def parse_hexa_fixed(self, l):
        d=8
#        cards= [l[d*i:d*(i+1)].strip() for i in range(23)]
        cards = re.findall('.'*d, l)
        return cards
    def parse_quad8_fixed(self, l):
        d=8
#        cards= [l[d*i:d*(i+1)].strip() for i in range(11)]
        cards = re.findall('.'*d, l)
        return cards
    def parse_quad4_fixed(self, l):
        d=8
#        cards= [l[d*i:d*(i+1)].strip() for i in range(11)]
        cards = re.findall('.'*d, l)
        return cards        
    def parse_pshell_fixed(self, l):
        d=8
#        cards= [l[d*i:d*(i+1)].strip() for i in range(2)]
        cards = re.findall('.'*d, l)
        return cards
    def parse_psolid_fixed(self, l):
        d=8
        cards = re.findall('.'*d, l)
#        cards= [l[d*i:d*(i+1)].strip() for i in range(2)]
        return cards

def write_nas2mfem(filename,  reader, exclude_bdr = None, offset=None):

        geom_type = {'TETRA': 4,
                     'TRIA6': 2,
                     'TRIA3': 2,
                     'HEXA':  5,
                     'QUAD8': 3,
                     'QUAD4': 3,}                             
        '''                     
        SEGMENT = 1
        TRIANGLE = 2
        SQUARE = 3
        TETRAHEDRON = 4
        CUBE = 5
        '''

        if exclude_bdr is None: exclude_bdr = [] 
        if offset is None: offset = [0.0, 0.0, 0.0]
        if reader.dataset is None:
            reader.load()
        print('loading (done)')
        data = reader.dataset
        fid = open(filename, 'w')

        grid = data['GRIDS']
        elems = data['ELEMS']
        
        el_3d = ['TETRA','HEXA']
        if 'TETRA' in elems:
            el_2d = ['TRIA6','TRIA3']
        else:
            el_2d = ['QUAD8','QUAD4']

        unique_grids = list(np.unique(np.hstack([elems[name].flatten() for name in el_3d+el_2d if name in elems])))
        print('unique_grid (done)')
        nvtc = len(unique_grids)
        ndim = grid.shape[-1]
        nelem = 0
        nbdry = 0
        
        for k in elems:
            if k in el_3d: nelem = nelem + len(elems[k+'_ATTR'])
            if k in el_2d:
                tmp = [x for x in elems[k+'_ATTR'] if not x in exclude_bdr]
                nbrdy = nbdry + len(tmp)
        
        
        fid.write('MFEM mesh v1.0\n')
        fid.write('\n')
        fid.write('dimension\n')
        fid.write(str(ndim) + '\n')
        fid.write('\n')
        fid.write('elements\n')
        fid.write(str(nelem) + '\n')
        
        rev_map = {unique_grids[x]:x for x in range(len(unique_grids))}
        for name in el_3d:
            if not name in elems: continue            
            vidx = elems[name]
            attr = elems[name+'_ATTR']
            gtyp = geom_type[name]
            txts = [None]*len(attr)
            for i in range(len(attr)):
                txt = [str(attr[i]), str(gtyp)]
#                txt.extend([str(unique_grids.index(x)) for x in vidx[i]])
                txt.extend([str(rev_map[x]) for x in vidx[i]])
                txts[i] = ' '.join(txt)
            fid.write('\n'.join(txts))
        fid.write('\n')                
        fid.write('boundary\n')
        fid.write(str(nbrdy) + '\n')
        for name in el_2d:
            if not name in elems: continue
            vidx = elems[name]
            attr = elems[name+'_ATTR']
            gtyp = geom_type[name]
            txts = [None]*len(attr)
            for i in range(len(attr)):
                if attr[i] in exclude_bdr: continue
                txt = [str(attr[i]), str(gtyp)]

#                txt.extend([str(unique_grids.index(x)) for x in vidx[i]])
                txt.extend([str(rev_map[x]) for x in vidx[i]])
                txts[i] = ' '.join(txt)
            fid.write('\n'.join(txts))                
        fid.write('\n')                
        fid.write('vertices\n')
        fid.write(str(nvtc) + '\n')                        
        fid.write(str(ndim) + '\n')
        txts = [None]*nvtc
        for i in range(nvtc):
            txt = [str(x+offset[kk]) for kk, x in enumerate(grid[unique_grids[i]])]
            txts[i] = ' '.join(txt)
        fid.write('\n'.join(txts))
        fid.close()

        
    
