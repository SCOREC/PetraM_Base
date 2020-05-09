'''

  variable-table

  a way to define model parameters and to generate associated
  methods

  definition

  name : 'tol'
  guilabel: 'tolelance (%)'
  type : 'any', 'float, 'int', 'complex', 'array', 'string', 'bool'

  special handling note: type == bool
     self.name + '_txt' stores value as boolean
     we use a checkbox interface.

  suffix : [('x', 'y', 'z'), ('x', 'y', 'z')]
  cb :   callback method name
  no_func: True: it can not become variable (use '=')
  tip : tip string
  readonly: text label
  example:

  Scalar : VtableElement('Tbdr',  type='float')
  Vector : VtableElement('Jsurf', type='float', 
                         suffix = ('x', 'y', 'z')
                         default = [0,0,0])
  Matrix : VtableElement('epsilonr', type='complex', 
                         suffix = [('x', 'y', 'z'), ('x', 'y', 'z')]
                         default = np.eye(3,3))

  StaticText :  VtableElement(None,
                              guilabel = 'Default Domain (Vac)',  
                              default =  'eps_r=1, mu_r=1, sigma=0')

                         
'''

import six
import numpy as np
import itertools
from collections import OrderedDict

import petram.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('Vtable')


class VtableElement(object):
    def __init__(self, name, type = '', 
                size  = (1,), suffix = None,
                cb = None, no_func = False,
                default = 0., guilabel = None, tip = '',
                default_txt = None, chkbox = False, 
                readonly = False):
        self.name = name
        self.readonly = readonly
        if not isinstance(type, str):
            assert False, "data type should be given as str"
        self.type = type
        self.chkbox = chkbox
        if suffix is None:
            self.shape = ()
            self.suffix = []
            self.ndim = 0
        else:
            ndim = 1 if isinstance(suffix[0], str) else 2
            if ndim == 1:
                self.shape = (len(suffix),)
                suffix = (suffix,)
            else:
               self.shape = tuple([len(x) for x in suffix])
            self.ndim = ndim
            self.suffix = [''.join(tmp) for tmp in itertools.product(*suffix)]
        self.cb = cb
        self.no_func = no_func
        if name is not None:
            if type=='string':
                self.default = default
            elif type=='array':
                self.default = default
            else:
                self.default = np.array(default, copy = False)
        else:
            self.default = default
        if len(self.shape) == 0:            
            if default_txt is not None:
                self.default_txt = default_txt
            else:
                self.default_txt = self.txt2value(self.default)
        self.guilabel = guilabel if guilabel is not None else self.name
        self.tip = tip

    def txt2value(self, txt):
        # note txt is not always text...
        if self.type == 'float': return float(txt)
        elif self.type == 'complex': return complex(txt)
        elif self.type == 'int': return int(txt)
        elif self.type == 'long': return long(txt)
        elif self.type == 'array':return txt
        elif self.type == 'string': return str(txt)
        elif self.type == 'bool': return bool(txt)        
        elif self.type == 'any': return txt
        elif self.type == '': return txt        
        return float(txt)
    
    def add_attribute(self, v):
        if self.name is None: return
        
        if self.type == 'bool':
            v[self.name + '_txt'] = self.default
            
        elif len(self.shape) == 0:
            v[self.name] = self.default_txt
            v[self.name + '_txt'] = self.default_txt
            if self.chkbox:
                v['use_' + self.name] = False
        else:
            values = [str(x) for x in self.default.flatten()]
            if len(values) != len(self.suffix):
                 raise ValueError("Length of defualt value does not match")
            suffix = ['_'+x for x in self.suffix]             
            for x, v_txt  in zip(suffix, values):
                v[self.name + x] = self.txt2value(v_txt)
                v[self.name + x + '_txt'] = str(v_txt)
            v[self.name + '_m'] =  self.default
            xxx = self.default.__repr__().split('(')[1].split(')')[0]
            v[self.name + '_m_txt'] =  ''.join(xxx.split("\n"))
            v['use_m_'+self.name] = False
            if self.chkbox:
                v['use_' + self.name] = False
        return v
    
    def panel_param(self, obj, validator = None):
        if self.name is None:
            return [self.guilabel, self.default,  2, {}]   
        chk_float   = (self.type == 'float')
        chk_int     = (self.type == 'int')
        chk_complex = (self.type == 'complex')
        chk_array   = (self.type == 'array')
        chk_string   = (self.type == 'string')
        
        if self.type == 'bool':
            value = getattr(obj, self.name + '_txt')            
            ret = [self.guilabel, value, 3, {"text":""}]
            return ret
        
        elif len(self.shape) == 0:
            value = getattr(obj, self.name + '_txt')
            ret = obj.make_phys_param_panel(self.guilabel,
                                            value, 
                                             no_func = self.no_func,
                                             chk_float = chk_float,
                                             chk_int   = chk_int,
                                             chk_complex = chk_complex,
                                             chk_array = chk_array,
                                             chk_string = chk_string)
            if self.readonly:
                ret[2] = ret[2]-10000
            if self.chkbox:
                ret =  [None, [True, [value]], 27, [{'text':'Use'},
                                                    {'elp': [ret]}],]
            return ret
        else:
            row = self.shape[0]
            col = self.shape[1] if self.ndim == 2 else 1
            suffix = ['_'+x for x in self.suffix]
            ret =  obj.make_matrix_panel(self.guilabel, suffix, row = row,
                                         col = col,
                                         validator = validator,
                                         chk_float = chk_float,
                                         chk_int   = chk_int, 
                                         chk_complex = chk_complex,
                                         no_func = self.no_func)
            if self.readonly:
                ret[2] = ret[2]-10000
            if self.chkbox:
                ret =  [None, None, 27, [{'text':'Use'},
                                         {'elp': [ret]}],]
            return ret

    def get_panel_value(self, obj):
        if self.name is None: return
                                            
        if self.type == 'bool':
            value = getattr(obj, self.name + '_txt')            
            return value
                                            
        elif len(self.shape) == 0:
            if self.chkbox:
                f = getattr(obj, 'use_' + self.name)
                v = getattr(obj, self.name + '_txt')
                return [f, [v]]
            else:
                return getattr(obj, self.name + '_txt')
        else:
            suffix = ['_'+x for x in self.suffix]        
            flag = getattr(obj, 'use_m_'+self.name)
            cb_value =  'Array Form' if flag else 'Elemental Form'
            a = [cb_value,
                [[str(getattr(obj, self.name+n+'_txt')) for n in suffix]],
                [str(getattr(obj, self.name + '_m_txt'))]]
            if self.chkbox:
                f = getattr(obj, 'use_' + self.name)
                return [f, [a]]                
            else:
                return a
            
    def import_panel_value(self, obj, v):
        if self.name is None: return

        if self.type == 'bool':
            setattr(obj, self.name + '_txt', bool(v))
        elif len(self.shape) == 0:
            if self.chkbox:
                setattr(obj, 'use_' + self.name, v[0])
                setattr(obj, self.name + '_txt', str(v[1][0]))                
            else:
                setattr(obj, self.name + '_txt', str(v))
        else:
            if self.chkbox:
                setattr(obj, 'use_' + self.name, v[0])
                v = v[1][0]
            suffix = ['_'+x for x in self.suffix]        
            setattr(obj, 'use_m_'+self.name,
                    (str(v[0]) == 'Array Form'))
            for k, n in enumerate(suffix):
                setattr(obj, self.name + n + '_txt', str(v[1][0][k]))
            setattr(obj, self.name + '_m_txt', str(v[2][0]))

    def preprocess_params(self, obj):
        '''
        if no_func, values are evaluated at this stage.
        otherwise, it only makes sure that values are string
        '''
        if self.name is None: return
                                            
        if self.type == 'bool':
            pass                                            
                                            
        elif len(self.shape) == 0:
            if self.no_func:
                value = obj.eval_phys_expr(str(getattr(obj,
                                                       self.name+'_txt')),
                                           self.name)[0]
                setattr(obj, self.name, value)
            else:
                setattr(obj, self.name,
                        str(getattr(obj, self.name + '_txt')))
        else:
            suffix = ['_'+x for x in self.suffix] + ['_m']
            for n in suffix:
                 setattr(obj, self.name + n,
                         str(getattr(obj, self.name + n + '_txt')))
                             
    def make_value_or_expression(self, obj):
        if self.name is None: return None

        kwargs = {}; kwargs['chk_'+self.type]=True
                                            
        if self.type == 'bool':
            return getattr(obj, self.name+'_txt')
                                            
        elif len(self.shape) == 0:
            if self.no_func:
                return getattr(obj, self.name)
            elif self.type == 'string':
                return str(getattr(obj, self.name))        
            else:
                v = getattr(obj, self.name)
                #print('v(before)', v)
                if str(v) == '':
                    v = str(self.default)
                #print('v(after)', v)                    
                var, f_name0 = obj.eval_phys_expr(v, self.name,
                                                  **kwargs)
                if f_name0 is None: return var
                return f_name0
        else:
            if getattr(obj, 'use_m_'+self.name):
                suffix = ['_m']                          
                eval_expr = obj.eval_phys_array_expr
            else:
                suffix = ['_'+x for x in self.suffix] 
                eval_expr = obj.eval_phys_expr         
            f_name = []
            for n in suffix:
               var, f_name0 = eval_expr(getattr(obj, self.name+n), self.name + n, **kwargs)
               if f_name0 is None:
                   f_name.append(var)
               else:
                   f_name.append(f_name0)
            return f_name
        
    def panel_tip(self):
        if self.name is None: return None                       
        return self.tip
    
class Vtable(OrderedDict):
    def attribute_set(self, v, keys = None):
        keys = keys if keys is not None else self.keys()
        for key in keys:
            v = self[key].add_attribute(v)
        return v

    def panel_param(self, obj, keys = None, validator = None):
        keys = keys if keys is not None else self.keys()
        return [self[key].panel_param(obj, validator = validator)
                for key in keys]
    
    def panel_tip(self, keys = None):
        keys = keys if keys is not None else self.keys()
        return [self[key].panel_tip() for key in keys]
                    
    def get_panel_value(self, obj, keys = None):
        keys = keys if keys is not None else self.keys()
        return [self[key].get_panel_value(obj) for key in keys]
                    
    def import_panel_value(self, obj, values, keys = None):
        keys = keys if keys is not None else self.keys()
        for k, v in zip(keys, values):
            self[k].import_panel_value(obj, v)
                    
    def preprocess_params(self, obj, keys = None):
        keys = keys if keys is not None else self.keys()
        for k in keys:
            self[k].preprocess_params(obj)
                    
    def make_value_or_expression(self, obj, keys = None):    
        keys = keys if keys is not None else self.keys()
        return [self[key].make_value_or_expression(obj) for key in keys]


    
class Vtable_mixin(object):
    def check_phys_expr(self, value, param, ctrl, **kwargs):
        try:
            self.eval_phys_expr(str(value), param, **kwargs)
            return True
        except:
            import petram.debug
            import traceback
            if petram.debug.debug_default_level > 2:
                traceback.print_exc()
            return False

    def check_phys_expr_int(self, value, param, ctrl):
        return self.check_phys_expr(value, param, ctrl, chk_int = True)

    def check_phys_expr_float(self, value, param, ctrl):
        return self.check_phys_expr(value, param, ctrl, chk_float = True)
     
    def check_phys_expr_complex(self, value, param, ctrl):
        return self.check_phys_expr(value, param, ctrl, chk_complex = True)
    
    def check_phys_expr_array(self, value, param, ctrl):
        return self.check_phys_expr(value, param, ctrl, chk_array = True)
     
    def check_phys_array_expr(self, value, param, ctrl, **kwargs):
        try:
            if not 'array' in self._global_ns:
               self._global_ns['array'] = np.array
            self.eval_phys_array_expr(str(value), param, **kwargs)
            return True
        except:
            import petram.debug
            import traceback
            if petram.debug.debug_default_level > 2:
               traceback.print_exc()
            return False
         
    def check_phys_array_expr_int(self, value, param, ctrl):
        return self.check_phys_array_expr(value, param, ctrl, chk_int = True)

    def check_phys_array_expr_float(self, value, param, ctrl):
        return self.check_phys_array_expr(value, param, ctrl, chk_float = True)

    def check_phys_array_expr_complex(self, value, param, ctrl):
        return self.check_phys_array_expr(value, param, ctrl, chk_complex = True)

    def eval_phys_expr(self, value, param,
                       chk_int = False, chk_complex = False, 
                       chk_float = False, chk_array = False,
                       chk_any = False):
        def dummy():
            pass
        if value.startswith('='):
            return dummy,  '='.join(value.split('=')[1:])
        else:
            if value.strip()=='': return None, None
            x = eval(value, self._global_ns, self._local_ns)
            if chk_any:
                pass
            elif chk_int:
                x = int(x)
            elif chk_complex:
                x = complex(x)
            elif chk_float:
                x = float(x)
            elif chk_array:
                x = np.atleast_1d(np.array(x, copy= False))
            else:
                x = x + 0   # at least check if it is number.
            dprint2('Value Evaluation ', param, '=', x)            
            return x, None
         
    def eval_phys_array_expr(self, value, param, chk_complex = False,
                             chk_float = False, chk_int = False):
        def dummy():
            pass
        if value.startswith('='):
            return dummy,  value.split('=')[1]           
        else:
            if not 'array' in self._global_ns:
               self._global_ns['array'] = np.array
            x = eval('array('+value+')', self._global_ns, self._local_ns)
            if chk_int:
                x = x.astype(int)
            elif chk_complex:
                x = x.astype(complex)
            elif chk_float:
                x = x.astype(float)
            else:
                x = x + 0   # at least check if it is number.
            dprint2('Value Evaluation ', param, '=', x)            
            return x, None
         
    # param_panel (defined in NS_mixin) verify if expression can be evaluated
    # phys_param_panel verify if the value is actually float.
    # it forces the number to become float after evaulating the expresison
    # using namespace.     
    def make_phys_param_panel(self, base_name, value, no_func = True,
                              chk_int = False,
                              chk_complex = False,
                              chk_float = False,
                              chk_array = False,
                              chk_string = False,
                              validator = None):
        if validator is None:
            if chk_int:
                validator = self.check_phys_expr_int
            elif chk_float:
                validator = self.check_phys_expr_float
            elif chk_complex:
                validator = self.check_phys_expr_complex
            elif chk_string:
                validator = None
            elif chk_array:
                validator = self.check_phys_expr_array
            else:
                validator = self.check_phys_expr

        if no_func:
            return  [base_name + "(=)",  value, 0,  
                     {'validator': validator,
                     'validator_param':base_name}]
        elif chk_string:
            return  [base_name,  value, 0,  {}]
        else:
            return  [base_name + "(*)",  value, 0,  
                     {'validator':   validator,
                     'validator_param':base_name}]

    def make_matrix_panel(self, base_name, suffix, row = 1, col = 1,
                          chk_int = False,
                          chk_complex = False,
                          chk_float = False,
                          validator = None,
                          no_func = False):
        if validator is None:
           
            if chk_int:
                validator = self.check_phys_expr_int
                validatora= self.check_phys_array_expr_int           
            elif chk_float:
                validator = self.check_phys_expr_float           
                validatora= self.check_phys_array_expr_float   
            elif chk_complex:
                validator = self.check_phys_expr_complex
                validatora= self.check_phys_array_expr_complex
            else:
                validator = self.check_phys_expr
                validatora= self.check_phys_array_expr       

        a = [ {'validator': validator,
               'validator_param':base_name + n} for n in suffix]
        elp1 = [[None, None, 43, {'row': row,
                                  'col': col,
                                 'text_setting': a}],]
        elp2 = [[None, None, 0, {'validator': validatora,
                                 'validator_param': base_name + '_m'},]]

        if no_func:
            label = base_name + '(=) '
        else:
            label = base_name + '(*) '
        ll = [None, None, 34, ({'text': label,
                                'choices': ['Elemental Form', 'Array Form'],
                                'call_fit': False},
                                {'elp': elp1},  
                                {'elp': elp2},),]
        return ll

    
