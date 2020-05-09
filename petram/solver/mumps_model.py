import numpy as np
import scipy
import weakref

import petram.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('MUMPSModel')

from petram.helper.matrix_file import write_matrix, write_vector, write_coo_matrix

from .solver_model import LinearSolverModel, LinearSolver

class MUMPS(LinearSolverModel):
    has_2nd_panel = False
    accept_complex = True
    is_iterative = False    
    def __init__(self):
        self.s = None
        LinearSolverModel.__init__(self)
        
    def init_solver(self):
        pass
    def panel1_param(self):
        return [["log_level(0-2)",   self.log_level,  400, {}],
                ["ordering",   self.ordering,  4, {"readonly": True,
                      "choices": ["auto", "Metis", "ParMetis", "PT-Scotch"]}],
                ["out-of-core",  self.out_of_core,  3, {"text":""}],
                ["error analysis",   self.error_ana,  4, {"readonly": True,
                      "choices": ["none", "full stat.", "main stat."]}],
                ["write matrix",  self.write_mat,   3, {"text":""}],
#                ["centralize matrix",  self.central_mat,   3, {"text":""}],
                ["use BLR",  self.use_blr,   3, {"text":""}],
                ["BLR drop parameter",  self.blr_drop,   300, {}],
                ["WS Inc. (ICNTL14)",  self.icntl14,   400, {}],
                ["WS Size (ICNTL23)",  self.icntl23,   400, {}],]        
    
    def get_panel1_value(self):
        return (int(self.log_level), self.ordering, self.out_of_core,
                self.error_ana, self.write_mat, #self.central_mat,
                self.use_blr, self.blr_drop, self.icntl14, self.icntl23)
    
    def import_panel1_value(self, v):
        self.log_level = int(v[0])
        self.ordering = str(v[1])
        self.out_of_core = v[2]
        self.error_ana = v[3]                
        self.write_mat = v[4]
        #self.central_mat = v[5]
        self.use_blr = v[5]
        self.blr_drop = v[6]
        self.icntl14 = v[7]
        self.icntl23 = v[8]        
        
    def attribute_set(self, v):
        v = super(MUMPS, self).attribute_set(v)
        
        v['log_level'] = 0
        '''
        1 : Only error messages printed.
        2 : Errors, warnings, and main statistics printed.
        3 : Errors and warnings and terse diagnostics 
            (only first ten entries of arrays) printed.
        4 : Errors, warnings and information on input, output parameters printed
        '''
        v['out_of_core'] = False
        v['write_mat'] = False
        v['central_mat'] = False
        v['ordering'] = 'auto'
        v['error_ana'] = 'none'
        v['use_blr'] = False
        v['blr_drop'] = 0.0
        v['icntl14'] = 20
        v['icntl23'] = 0
        v['use_single_precision'] = False

        # this flag needs to be set, so that destcuctor works when model tree is loaded from 
        # pickled file
        v['s'] = None
        return v
    
    def linear_system_type(self, assemble_real, phys_real):
        if phys_real: return 'coo'
        if assemble_real: return 'coo_real'
        return 'coo'
    
    def allocate_solver(self, is_complex = False, engine=None):
        # engine not used
        solver = MUMPSSolver(self, engine)
        solver.AllocSolver(is_complex, self.use_single_precision)
        return solver
    
    def solve(self, engine, A, b):
        '''        
        if reuse_factor:
            return self.solve_reuse_factor(engine, A, b)
        elif engine.is_matrix_distributed:

            if self.central_mat:
                # in this case, we collect all matrix data to root
                # and re-define A on the root node
                dprint1("centralizing distributed matrix")                               
                shape =A.shape
                col = gather_vector(A.col)
                row = gather_vector(A.row)
                data = gather_vector(A.data)
                if myid == 0:
                    A = scipy.sparse.coo_matrix((data,(row, col)),
                                                  shape = shape,
                                                  dtype = A.dtype)
                dprint1("calling solve_central_matrix")
                return self.solve_central_matrix(engine, A, b)
            else:
            dprint1("calling solve_distributed_matrix")
            return self.solve_distributed_matrix(engine, A, b)
        else:

            dprint1("calling solve_central_matrix")                            
            ret = self.solve_central_matrix(engine, A, b)
            return ret

            '''
        solver = self.allocate_solver((A.dtype == 'complex'), engine)
        solver.SetOperator(A, dist = engine.is_matrix_distributed)
        solall = solver.Mult(b, case_base=engine.case_base)
        return solall
            

    def real_to_complex(self, solall, M=None):
        try:
            from mpi4py import MPI
        except:
            from petram.helper.dummy_mpi import MPI
        myid     = MPI.COMM_WORLD.rank
        nproc    = MPI.COMM_WORLD.size
        
        if myid == 0:        
           s = solall.shape[0]
           solall = solall[:s//2,:] + 1j*solall[s//2:,:]
           return solall
       
    def __del__(self):
        if self.s is not None:
            self.s.finish()
        self.s = None
        
class MUMPSSolver(LinearSolver):
    is_iterative = False
    def __init__(self, *args, **kwargs):
        super(MUMPSSolver, self).__init__(*args, **kwargs)
        self.silent = False
        
    def set_silent(self, silent):
        self.silent = silent
        
    def set_ordering_flag(self, s):
        from petram.mfem_config import use_parallel
        gui = self.gui
        if gui.ordering == 'auto':
            pass
        elif gui.ordering == 'Metis':
            s.set_icntl(28,  1)
            s.set_icntl(7,  5)                            
        elif gui.ordering == 'ParMetis' and use_parallel:
            s.set_icntl(28,  2)
            s.set_icntl(29,  2)
        elif gui.ordering == 'ParMetis' and not use_parallel:            
            dprint1("!!! ParMetis ordering is selected. But solver is not in parallel mode. Ignored")            
        elif gui.ordering == 'PT-Scotch' and use_parallel:
            s.set_icntl(28,  2)            
            s.set_icntl(29,  1)
        elif gui.ordering == 'PT-Scotch' and not use_parallel:
            dprint1("!!! PT-Scotch ordering is selected. But solver is not in parallel mode. Ignored")
        else:
            pass
        #s.set_icntl(28,  2)                
        
    def set_error_analysis(self, s):
        from petram.mfem_config import use_parallel
        gui = self.gui
        if gui.error_ana == 'none':
            s.set_icntl(11,  0)
        elif gui.error_ana == 'main stat.':
            s.set_icntl(11,  2)                        
        elif gui.error_ana == 'full stat.':
            s.set_icntl(11,  1)
        else:
            pass
        
    def AllocSolver(self, is_complex, use_single_precision):
        if is_complex:
            if use_single_precision:
                from petram.ext.mumps.mumps_solve import c_array as data_array
                from petram.ext.mumps.mumps_solve import CMUMPS                
                s = CMUMPS()                
            else:
                from petram.ext.mumps.mumps_solve import z_array as data_array
                from petram.ext.mumps.mumps_solve import ZMUMPS                                
                s = ZMUMPS()
        else:
            if use_single_precision:
                from petram.ext.mumps.mumps_solve import s_array as data_array
                from petram.ext.mumps.mumps_solve import SMUMPS                                
                s = SMUMPS()
            else:
                from petram.ext.mumps.mumps_solve import d_array as data_array
                from petram.ext.mumps.mumps_solve import DMUMPS                
                s = DMUMPS()
           
        self.s = s
        self.is_complex = is_complex
        self.data_array = data_array

        gui = self.gui
        # No outputs
        if gui.log_level == 0:
            s.set_icntl(1, -1)
            s.set_icntl(2, -1)
            s.set_icntl(3, -1)
            s.set_icntl(4,  0)
        elif gui.log_level == 1:
            pass
        else:
            s.set_icntl(1,  6)            
            s.set_icntl(2,  6)
            s.set_icntl(3,  6)            
            s.set_icntl(4,  6)

    def make_matrix_entries(self, A):
        if self.gui.use_single_precision:
            if self.is_complex:
                AA = A.data.astype(np.complex64, copy=False)
            else:
                AA = A.data.astype(np.float32, copy=False)
        else:
            AA = A.data
        return AA
            
    def make_vector_entries(self, B):
        if self.gui.use_single_precision:
            if self.is_complex:
                return B.astype(np.complex64, copy=False)
            else:
                return B.astype(np.float32, copy=False)
        else:
            return B
        
    def SetOperator(self, A, dist, name=None):
        try:
            from mpi4py import MPI
        except:
            from petram.helper.dummy_mpi import MPI
        myid     = MPI.COMM_WORLD.rank
        nproc    = MPI.COMM_WORLD.size

        from petram.ext.mumps.mumps_solve import i_array
        gui = self.gui
        s = self.s
        if dist:
            dprint1("SetOperator distributed matrix")
            A.eliminate_zeros()
            if gui.write_mat:
                write_coo_matrix('matrix', A)

            import petram.ext.mumps.mumps_solve as mumps_solve
            dprint1('!!!these two must be consistent')
            dprint1('sizeof(MUMPS_INT) ' , mumps_solve.SIZEOF_MUMPS_INT())
            #dprint1('index data size ' , type(A.col[0]))
            #dprint1('matrix data type ' , type(A.data[0]))

            s.set_icntl(5,0)
            s.set_icntl(18,3)

            dprint1("NNZ local: ", A.nnz)
            nnz_array = np.array(MPI.COMM_WORLD.allgather(A.nnz))
            if myid ==0:
                dprint1("NNZ all: ", nnz_array, np.sum(nnz_array))            
                s.set_n(A.shape[1])
            dtype_int = 'int'+str(mumps_solve.SIZEOF_MUMPS_INT()*8)
            row = A.row
            col = A.col
            row = row.astype(dtype_int) + 1
            col = col.astype(dtype_int) + 1
            AA = self.make_matrix_entries(A)

            if len(col) > 0:
                dprint1('index data size ' , type(col[0]))
                dprint1('matrix data type ' , type(AA[0]))

            s.set_nz_loc(len(A.data))
            s.set_irn_loc(i_array(row))
            s.set_jcn_loc(i_array(col))
            s.set_a_loc(self.data_array(AA))

            s.set_icntl(14, gui.icntl14)
            s.set_icntl(23, gui.icntl23)            
            s.set_icntl(2, 1)

            self.dataset = (A.data, row, col)
        else:
            A = A.tocoo(False)#.astype('complex')
            import petram.ext.mumps.mumps_solve as mumps_solve
            dprint1('!!!these two must be consistent')
            dprint1('sizeof(MUMPS_INT) ' , mumps_solve.SIZEOF_MUMPS_INT())

            dtype_int = 'int'+str(mumps_solve.SIZEOF_MUMPS_INT()*8)

            if gui.write_mat:
                #tocsr().tocoo() forces the output is row sorted.
                write_coo_matrix('matrix', A.tocsr().tocoo())
            # No outputs
            if myid ==0:
                row = A.row
                col = A.col
                row = row.astype(dtype_int) + 1
                col = col.astype(dtype_int) + 1
                AA = self.make_matrix_entries(A)                        
                
                if len(col) > 0:
                    dprint1('index data size ' , type(col[0]))
                    dprint1('matrix data type ' , type(AA[0]))

                s.set_n(A.shape[0])
                s.set_nz(len(A.data))
                s.set_irn(i_array(row))
                s.set_jcn(i_array(col))
                s.set_a(self.data_array(AA))
                self.dataset = (A.data, row, col)                
            s.set_icntl(14,  gui.icntl14)
            s.set_icntl(23, gui.icntl23)                        
            s.set_icntl(6,  5)    # column permutation

        # blr
        if gui.use_blr:   
            s.set_icntl(35,1)
            s.set_cntl(7, float(gui.blr_drop))
            
        self.set_ordering_flag(s)

        # out-of-core
        if gui.out_of_core:
           s.set_icntl(22,  1)            
        MPI.COMM_WORLD.Barrier()
        dprint1("job1")
        s.set_job(1)
        s.run()
        info1 = s.get_info(1)

        if info1 != 0:
            assert False, "MUMPS call (job1) faield. Check error log"

        MPI.COMM_WORLD.Barrier()
        dprint1("job2")
        s.set_icntl(24, 1)
        s.set_job(2)
        s.run()
        info1 = s.get_info(1)
        if info1 != 0:
            assert False, "MUMPS call (job2) faield. Check error log"
    

    def Mult(self, b, x=None, case_base=0):
        try:
            from mpi4py import MPI
        except:
            from petram.helper.dummy_mpi import MPI
        myid     = MPI.COMM_WORLD.rank
        nproc    = MPI.COMM_WORLD.size
        
        #self.SetOperator(A, b, True, engine)
        gui = self.gui
        s = self.s
        if gui.write_mat:
            if myid == 0:
                 for ib in range(b.shape[1]):
                     write_vector('rhs_'+str(ib + case_base), b[:,ib])
                 case_base = case_base + b.shape[1]
            else: case_base = None
            case_base = MPI.COMM_WORLD.bcast(case_base, root=0)
        if myid == 0:
            s.set_lrhs_nrhs(b.shape[0], b.shape[1])
            bstack = np.hstack(np.transpose(b))
            bstack = self.make_vector_entries(bstack)
            s.set_rhs(self.data_array(bstack))

        if not self.silent:
            dprint1("job3")
        if self.silent:
            s.set_icntl(1, -1)
            s.set_icntl(2, -1)
            s.set_icntl(3, -1)
            s.set_icntl(4,  0)

        info1 = s.get_info(1)
        if info1 != 0:
            assert False, "MUMPS call (job3) faield. Check error log"
            
        self.set_error_analysis(s)        
        s.set_job(3)
        s.run()
        #s.finish()
        
        rsol = None; isol = None; sol_extra = None
        if (myid == 0):
            if self.is_complex:
                sol = s.get_real_rhs()+1j*s.get_imag_rhs()
            else:
                sol = s.get_real_rhs()
            sol = np.transpose(sol.reshape(-1, len(b)))
            return sol

from petram.mfem_config import use_parallel
if use_parallel:
   from petram.helper.mpi_recipes import *
   from mfem.common.parcsr_extra import *
   import mfem.par as mfem
else:
   import mfem.ser as mfem

class MUMPSPreconditioner(mfem.PyOperator):
    def __init__(self, A0, gui=None, engine=None, silent=False, **kwargs):
        mfem.PyOperator.__init__(self, A0.Height())
        self.gui = gui
        self.engine = engine
        self.silent = silent
        self.is_complex_operator = False
        
        if 'single' in kwargs and not 'double' in kwargs:
            self.single = kwargs.pop('single')
            self.gui.use_single_precision = self.single
        elif not 'single' in kwargs and 'double' in kwargs:
            self.single = not kwargs.pop('double')
            self.gui.use_single_precision = self.single
        elif 'single' in kwargs and 'double' in kwargs:            
            assert False, "singel and double can not be uset together"
        else:
            pass
            
        self.SetOperator(A0)

    def SetOperator(self, opr):
        def isSparseMatrix(opr):
            return isinstance(opr, mfem.SparseMatrix)
        
        check = opr._real_operator if isinstance(opr, mfem.ComplexOperator) else opr

        if isSparseMatrix(check):
            from mfem.common.sparse_utils import sparsemat_to_scipycsr

            if isinstance(opr, mfem.ComplexOperator):
                mat = ( sparsemat_to_scipycsr(opr._real_operator, float) + 
                        sparsemat_to_scipycsr(opr._imag_operator, float) * 1j)
                coo_opr = mat.tocoo()
                self.is_complex_operator = True
            else:
                coo_opr = sparsemat_to_scipycsr(opr, float).tocoo()
                
            self.solver = MUMPSSolver(self.gui, self.engine)
            self.solver.AllocSolver(self.is_complex_operator,
                                    self.gui.use_single_precision)
            self.solver.SetOperator(coo_opr, False)
            self.row_part = [-1,-1]
            
        else:
            from mfem.common.parcsr_extra import ToScipyCoo
            from scipy.sparse import coo_matrix

            if isinstance(opr, mfem.ComplexOperator):
                lcsr = (ToScipyCoo(opr._real_operator).tocsr() + 
                        ToScipyCoo(opr._imag_operator).tocsr()*1j)
                lcoo = lcsr.tocoo()
                shape = (opr._real_operator.GetGlobalNumRows(),
                         opr._real_operator.GetGlobalNumCols())                

                rpart = opr._real_operator.GetRowPartArray()
                self.is_complex_operator = True
                self.row_part = rpart
            else:
                lcoo = ToScipyCoo(opr)
                shape = (opr.GetGlobalNumRows(), opr.GetGlobalNumCols())
                rpart = opr.GetRowPartArray()                
                self.row_part = rpart  
              
            gcoo = coo_matrix(shape)
            gcoo.data = lcoo.data
            gcoo.row = lcoo.row + rpart[0]
            gcoo.col = lcoo.col
            self.solver = MUMPSSolver(self.gui, self.engine)
            self.solver.AllocSolver(self.is_complex_operator,
                                    self.gui.use_single_precision)
            self.solver.SetOperator(gcoo, True)
            self.is_parallel=True            

        self.solver.set_silent(self.silent)
            
    def Mult(self, x, y):
        # in the parallel enviroment, we need to collect x and
        # redistribute y
        # we keep RowPart array from opr since here y is
        # vector not ParVector even in the parallel env.
        try:
            from mpi4py import MPI
        except:
            from petram.helper.dummy_mpi import MPI
        myid     = MPI.COMM_WORLD.rank
        nproc    = MPI.COMM_WORLD.size
        
        if self.is_complex_operator:
            vec = x.GetDataArray()
            ll = vec.size
            vec = vec[:ll//2] + 1j*vec[ll//2:]
        else:
            vec = x.GetDataArray()

        if self.row_part[0] == -1:
            xx = np.atleast_2d(vec).transpose()
        else:
            from mpi4py import MPI
            comm = MPI.COMM_WORLD
            from petram.helper.mpi_recipes import gather_vector
            xx = gather_vector(vec)
            if myid == 0:
                xx = np.atleast_2d(xx).transpose()
                
        s=self.solver.Mult(xx)
        
        if self.row_part[0] != -1:
            from mpi4py import MPI
            comm = MPI.COMM_WORLD
            s = comm.bcast(s)
            s = s[self.row_part[0]:self.row_part[1]]

        if self.is_complex_operator:
            s = np.hstack((s.real.flatten(), s.imag.flatten()))

        y.Assign(s.flatten())
     
