import numpy as np

from petram.model import Domain, Bdry, Edge, Point, Pair
from petram.phys.coefficient import SCoeff, VCoeff
from petram.phys.phys_model import Phys, PhysModule

import petram.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('WF_Essential')

from petram.mfem_config import use_parallel
if use_parallel:
   import mfem.par as mfem
else:
   import mfem.ser as mfem

from petram.phys.vtable import VtableElement, Vtable
from mfem.common.mpi_debug import nicePrint

class WF_Essential(Bdry, Phys):
    has_essential = True
    nlterms = []
    can_timedpendent = True
    has_3rd_panel = True            
    def __init__(self, **kwargs):
        super(WF_Essential, self).__init__( **kwargs)

    def attribute_set(self, v):
        Bdry.attribute_set(self, v)
        Phys.attribute_set(self, v)         
        v['sel_readonly'] = False
        v['sel_index'] = []
        return v
        
    @property
    def vt(self):
        root_phys = self.get_root_phys()
        if not isinstance(root_phys, PhysModule):
             data =  (('esse_value', VtableElement(None, type="array",
                                                   guilabel = "dummy",
                                                   default = "0.0",
                                                   tip = "dummy" )),)
             return Vtable(data)

        dep_vars = self.get_root_phys().dep_vars
        if not hasattr(self, '_dep_var_bk'):
            self._dep_var_bk = ""

        if self._dep_var_bk != dep_vars:
            dep_var = dep_vars[0]
            data =  (('esse_value', VtableElement("esse_value", type="array",
                                                   guilabel = dep_var,
                                                   default =   "0.0",
                                                   tip = "Essentail BC" )),
                      ('esse_vdim', VtableElement("esse_vdim", type="string",
                                                   guilabel = "vdim (0-base)",
                                                   default =   "all",
                                                   #readonly = True, 
                                                   tip = "vdim (not supported)")),)
            vt = Vtable(data)
            self._vt1 = vt
            self._dep_var_bk = dep_vars            
            self.update_attribute_set()            
        else:
            vt = self._vt1
        return vt
        
    def get_essential_idx(self, kfes):
        if kfes == 0:
            return self._sel_index
        else:
            return []

    def apply_essential_1(self, method, real, c0, vdim, vvdim, bdr_attr):
        if vdim == 1:
           coeff1 = SCoeff(c0, self.get_root_phys().ind_vars,
                           self._local_ns, self._global_ns,
                           real = real)
        else:
           coeff1 = VCoeff(vdim, c0, self.get_root_phys().ind_vars,
                           self._local_ns, self._global_ns,
                           real = real)

        assert not (vvdim != -1 and vdim > 1), "Wrong setting...(vvdim != -1 and vdim > 1)"
        #print vvdim, vdim, method, coeff1
        if vvdim == -1:
            method(coeff1, mfem.intArray(bdr_attr))
        else:
            for cp in vvdim:
                method(coeff1, mfem.intArray(bdr_attr), cp)
                
         
    def apply_essential(self, engine, gf, real = False, kfes = 0):
        if kfes > 0: return
        c0, vdim0 = self.vt.make_value_or_expression(self)
        
        if real:       
            dprint1("Apply Ess.(real)" + str(self._sel_index), 'c0, v0', c0, vdim0)
        else:
            dprint1("Apply Ess.(imag)" + str(self._sel_index), 'c0, v0', c0, vdim0)
            
        name =  self.get_root_phys().dep_vars[0]
        fes = engine.get_fes(self.get_root_phys(), name=name)

        vdim = fes.GetVDim()
        vvdim = -1
        
        if vdim0 != 'all':
            lvdim = len(self.esse_vdim.split(","))
            #assert lvdim == 1, "Specify only one vdim"            
            vvdim = [int(x) for x in self.esse_vdim.split(",")]
        else:
           vvdim = -1
      
        fec_name = fes.FEColl().Name()
        
        mesh = engine.get_emesh(mm = self)        
        ibdr = mesh.bdr_attributes.ToList()

        bdr_attr = [0]*mesh.bdr_attributes.Max()
        for idx in self._sel_index:
            bdr_attr[idx-1] = 1

        if fec_name.startswith("ND"):
            assert vdim == 1, "ND element vdim must be one"
            vdim = mesh.Dimension()
            method = gf.ProjectBdrCoefficientTangent
            self.apply_essential_1(method, real, c0, vdim, vvdim, bdr_attr)
            
        elif fec_name.startswith("RT"):
            assert vdim == 1, "RT element vdim must be one"            
            vdim = mesh.Dimension()
            method = gf.ProjectBdrCoefficientNormal
            self.apply_essential_1(method, real, c0, vdim, vvdim, bdr_attr)
            
        #elif self.get_root_phys().vdim == 1:
        #    ProjectBdrCoefficient does not realy work in parallel
        #    since shadow vertex are not always set...
        #    method = gf.ProjectBdrCoefficient           
        #    self.apply_essential_1(method, real, c0, vdim, vvdim, bdr_attr)

        else: #H1 or L2
            # vector field FE. 
            method = gf.ProjectCoefficient
            ess_vdofs = mfem.intArray()
            fes.GetEssentialVDofs(mfem.intArray(bdr_attr), ess_vdofs, 0)
            vdofs = np.where(np.array(ess_vdofs.ToList()) == -1)[0]
            dofs = mfem.intArray([fes.VDofToDof(i) for i in vdofs])
            fes.BuildDofToArrays()
            
            if self.get_root_phys().vdim == 1:
                coeff1 = SCoeff(c0, self.get_root_phys().ind_vars,
                                self._local_ns, self._global_ns,
                                real = real)
                gf.ProjectCoefficient(coeff1, dofs, 0)
               
            elif vdim0 == 'all':
                coeff1 = VCoeff(vdim, c0, self.get_root_phys().ind_vars,
                           self._local_ns, self._global_ns,
                           real = real)
                gf.ProjectCoefficient(coeff1, dofs)
            else:
                for k, cp in enumerate(vvdim):
                    coeff1 = SCoeff(c0, self.get_root_phys().ind_vars,
                                    self._local_ns, self._global_ns,
                                    real = real, component=k)
                    gf.ProjectCoefficient(coeff1, dofs, cp)




                   
                
            
