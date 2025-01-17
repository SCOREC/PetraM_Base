from petram.phys.vtable import VtableElement, Vtable, Vtable_mixin
from petram.namespace_mixin import NS_mixin
from .solver_model import SolverBase

import petram.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('SolveControl')
format_memory_usage = debug.format_memory_usage


class SolveControl(SolverBase):
    has_2nd_panel = False


data = [("max_count", VtableElement("max_count",
                                    type='int',
                                    guilabel="Max count",
                                    default=3,
                                    tip="parameter range",))]


class ForLoop(SolveControl, NS_mixin, Vtable_mixin):
    vt_loop = Vtable(data)

    def __init__(self, *args, **kwargs):
        SolveControl.__init__(self, *args, **kwargs)
        NS_mixin.__init__(self, *args, **kwargs)

    def attribute_set(self, v):
        v['phys_model'] = ''
        v['init_setting'] = ''
        v['postprocess_sol'] = ''
        v['dwc_name'] = ''
        v['use_dwc'] = False
        v['dwc_args'] = ''
        v['counter_name'] = 'loop_counter'
        self.vt_loop.attribute_set(v)

        super(ForLoop, self).attribute_set(v)
        return v

    def get_possible_child(self):
        from petram.solver.solver_model import SolveStep
        from petram.solver.parametric import Parametric
        return [SolveStep, Parametric, Break, Continue, DWCCall]

    def panel1_param(self):
        panels = self.vt_loop.panel_param(self)

        ret1 = [["dwc", self.dwc_name, 0, {}, ],
                ["args.", self.dwc_args, 0, {}, ], ]
        value1 = [self.dwc_name, self.dwc_args]
        panel2 = [[None, [False, value1, ], 27, [{'text': 'Use DWC (postprocess)'},
                                                 {'elp': ret1}, ]], ]

        return ([["Postporcess solution", self.postprocess_sol, 0, {}, ],
                 ["Counter name", self.counter_name, 0, {}, ]] + panels + panel2)

    def get_panel1_value(self):
        val = self.vt_loop.get_panel_value(self)

        return (  # self.init_setting,
            self.postprocess_sol,
            self.counter_name,
            val[0],
            [self.use_dwc, [self.dwc_name, self.dwc_args]])

    def import_panel1_value(self, v):
        #self.init_setting = v[0]
        self.postprocess_sol = v[0]
        self.counter_name = v[1]
        self.vt_loop.import_panel_value(self, (v[2],))
        self.use_dwc = v[3][0]
        self.dwc_name = v[3][1][0]
        self.dwc_args = v[3][1][1]

    def get_all_phys_range(self):
        steps = self.get_active_steps()
        ret0 = sum([s.get_phys_range() for s in steps], [])

        ret = []
        for x in ret0:
            if not x in ret:
                ret.append(x)

        return ret

    def get_active_steps(self, with_control=False):
        steps = []
        for x in self.iter_enabled():
            if not x.enabled:
                continue

            if isinstance(x, Break) and with_control:
                steps.append(x)
            elif isinstance(x, Continue) and with_control:
                steps.append(x)
            elif isinstance(x, DWCCall) and with_control:
                steps.append(x)
            elif len(list(x.iter_enabled())) > 0:
                steps.append(x)

        return steps

    def get_pp_setting(self):
        names = self.postprocess_sol.split(',')
        names = [n.strip() for n in names if n.strip() != '']
        return [self.root()['PostProcess'][n] for n in names]

    def run(self, engine, is_first=True):
        dprint1("!!!!! Entering SolveLoop :" + self.name() + " !!!!!")

        steps = self.get_active_steps(with_control=True)
        self.vt_loop.preprocess_params(self)
        max_count = self.vt_loop.make_value_or_expression(self)[0]

        for i in range(max_count):
            dprint1("!!!!! SolveLoop : Count = " + str(i))
            g = self._global_ns[self.counter_name] = i
            for s in steps:
                do_break = False
                do_continue = False
                if isinstance(s, Break):
                    do_break = s.run(engine, i)
                elif isinstance(s, Continue):
                    do_continue = s.run(engine, i)
                elif isinstance(s, DWCCall):
                    do_continue = s.run(engine, i)
                else:
                    s.run(engine, is_first=is_first)
                    if s.solve_error[0]:
                        dprint1(
                            "Loop failed " +
                            s.name() +
                            ":" +
                            s.solve_error[1])
                        break
                    is_first = False

                if do_break or do_continue:
                    break
            if do_break:
                break

        postprocess = self.get_pp_setting()
        engine.run_postprocess(postprocess, name=self.name())

        if self.use_dwc:
            engine.call_dwc(self.get_all_phys_range(),
                            method="postprocess",
                            callername=self.name(),
                            dwcname=self.dwc_name,
                            args=self.dwc_args)


class Break(SolveControl, NS_mixin):
    def __init__(self, *args, **kwargs):
        SolveControl.__init__(self, *args, **kwargs)
        NS_mixin.__init__(self, *args, **kwargs)

    def attribute_set(self, v):
        v['break_cond'] = ''
        v['use_dwc'] = False
        v['dwc_name'] = ''
        v['dwc_args'] = ''
        return super(Break, self).attribute_set(v)

    def panel1_param(self):
        ret0 = [["Break cond.", self.break_cond, 0, {}, ], ]
        ret1 = [["dwc", self.dwc_name, 0, {}, ],
                ["args.", self.dwc_args, 0, {}, ], ]
        value0 = [self.break_cond]
        value1 = [self.dwc_name, self.dwc_args]
        return [[None, [False, value1, value0], 127, [{'text': 'Use DWC (loopcontrol)'},
                                                      {'elp': ret1},
                                                      {'elp': ret0}]], ]

    def import_panel1_value(self, v):
        self.use_dwc = v[0][0]
        self.dwc_name = v[0][1][0]
        self.dwc_args = v[0][1][1]
        self.break_cond = v[0][2][0]

    def get_panel1_value(self):
        return ([self.use_dwc, [self.dwc_name, self.dwc_args],
                 [self.break_cond], ], )

    def get_all_phys_range(self):
        return self.parent.get_all_phys_range()

    def run(self, engine, count):
        if self.use_dwc:
            return engine.call_dwc(self.get_all_phys_range(),
                                   method="loopcontrol",
                                   callername=self.name(),
                                   dwcname=self.dwc_name,
                                   args=self.dwc_args,
                                   count=count,)
        else:
            if self.break_cond in self._global_ns:
                break_func = self._global_ns[self.break_cond]
            else:
                assert False, self.break_cond + " is not defined"
            g = self._global_ns
            code = "check =" + self.break_cond + '(count)'
            ll = {'count': count}
            exec(code, g, ll)

            return ll['check']


class Continue(SolveControl, NS_mixin):
    def __init__(self, *args, **kwargs):
        SolveControl.__init__(self, *args, **kwargs)
        NS_mixin.__init__(self, *args, **kwargs)

    def attribute_set(self, v):
        v['continue_cond'] = ''
        v['use_dwc'] = False
        v['dwc_name'] = ''
        v['dwc_args'] = ''
        return super(Continue, self).attribute_set(v)

    def panel1_param(self):
        ret0 = [["Continue cond.", self.continue_cond, 0, {}, ], ]
        ret1 = [["dwc", self.dwc_name, 0, {}, ],
                ["args.", self.dwc_args, 0, {}, ], ]
        value0 = [self.continue_cond]
        value1 = [self.dwc_name, self.dwc_args]
        return [[None, [False, value1, value0], 127, [{'text': 'Use DWC (loopcontrol)'},
                                                      {'elp': ret1},
                                                      {'elp': ret0}]], ]

    def import_panel1_value(self, v):
        self.use_dwc = v[0][0]
        self.dwc_name = v[0][1][0]
        self.dwc_args = v[0][1][1]
        self.continue_cond = v[0][2][0]

    def get_panel1_value(self):
        return ([self.use_dwc, [self.dwc_name, self.dwc_args],
                 [self.continue_cond], ], )

    def get_all_phys_range(self):
        return self.parent.get_all_phys_range()

    def run(self, engine, count):
        if self.use_dwc:
            return engine.call_dwc(self.get_all_phys_range(),
                                   method="loopcontrol",
                                   callername=self.name(),
                                   dwcname=self.dwc_name,
                                   args=self.dwc_args,
                                   count=count)
        else:
            if self.continue_cond in self._global_ns:
                c_func = self._global_ns[self.continue_cond]
            else:
                assert False, self.continue_cond + " is not defined"

            g = self._global_ns
            code = "check=" + self.continue_cond + '(count)'
            ll = {'count': count}
            exec(code, g, ll)

            return ll['check']


class DWCCall(SolveControl):
    '''
    standalone DWC caller
    '''

    def __init__(self, *args, **kwargs):
        SolverBase.__init__(self, *args, **kwargs)

    def attribute_set(self, v):
        v['dwc_args'] = ''
        v['dwc_name'] = ''
        super(DWCCall, self).attribute_set(v)
        return v

    def get_possible_child(self):
        return []

    def panel1_param(self):
        panels = [["dwc", self.dwc_name, 0, {}, ],
                  ["args.", self.dwc_args, 0, {}, ], ]

        return panels

    def get_panel1_value(self):
        return [self.dwc_name, self.dwc_args]

    def import_panel1_value(self, v):
        self.dwc_name = v[0]
        self.dwc_args = v[1]

    def get_target_phys(self):
        return []

    def get_all_phys(self):
        phys_root = self.root()['Phys']
        return [x for x in phys_root.iter_enabled()]

    def run(self, engine, is_first=True):
        engine.call_dwc(self.get_all_phys(),
                        method="call",
                        callername=self.name(),
                        dwcname=self.dwc_name,
                        args=self.dwc_args)
