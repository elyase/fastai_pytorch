
        #################################################
        ### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
        #################################################
        # file to edit: dev_nb/004_callbacks.ipynb

from nb_003 import *
from torch import Tensor,tensor
from fast_progress import master_bar,progress_bar
from fast_progress.fast_progress import MasterBar, ProgressBar
import re
from typing import Iterator

Floats = Union[float, Collection[float]]
PBar = Union[MasterBar, ProgressBar]

class OptimWrapper():
    "Normalize naming of parameters on wrapped optimizers"
    def __init__(self, opt:optim.Optimizer, wd:float=0., true_wd:bool=False):
        "Create wrapper for `opt` and optionally (`true_wd`) set weight decay `wd`"
        self.opt,self.true_wd = opt,true_wd
        self.opt_keys = list(self.opt.param_groups[0].keys())
        self.opt_keys.remove('params')
        self.read_defaults()
        self._wd = wd

    #Pytorch optimizer methods
    def step(self)->None:
        "Performs a single optimization step "
        # weight decay outside of optimizer step (AdamW)
        if self.true_wd:
            for pg in self.opt.param_groups:
                for p in pg['params']: p.data.mul_(1 - self._wd*pg['lr'])
            self.set_val('weight_decay', 0)
        self.opt.step()

    def zero_grad(self)->None:
        "Clears the gradients of all optimized `Tensor`s"
        self.opt.zero_grad()

    #Hyperparameters as properties
    @property
    def lr(self)->float:
        "Learning rate"
        return self._lr

    @lr.setter
    def lr(self, val:float)->None: self._lr = self.set_val('lr', val)

    @property
    def mom(self)->float:
        "Momentum if present on wrapped opt, else betas"
        return self._mom

    @mom.setter
    def mom(self, val:float)->None:
        "Momentum if present on wrapped opt, else betas"
        if 'momentum' in self.opt_keys: self.set_val('momentum', val)
        elif 'betas' in self.opt_keys:  self.set_val('betas', (val, self._beta))
        self._mom = val

    @property
    def beta(self)->float:
        "Beta if present on wrapped opt, else it's alpha"
        return self._beta

    @beta.setter
    def beta(self, val:float)->None:
        "Beta if present on wrapped opt, else it's alpha"
        if 'betas' in self.opt_keys:    self.set_val('betas', (self._mom,val))
        elif 'alpha' in self.opt_keys:  self.set_val('alpha', val)
        self._beta = val

    @property
    def wd(self)->float:
        "Weight decay for wrapped opt"
        return self._wd

    @wd.setter
    def wd(self, val:float)->None:
        "Weight decay for wrapped opt"
        if not self.true_wd: self.set_val('weight_decay', val)
        self._wd = val

    #Helper functions
    def read_defaults(self):
        "Reads in the default params from the wrapped optimizer"
        self._beta = None
        if 'lr' in self.opt_keys: self._lr = self.opt.param_groups[0]['lr']
        if 'momentum' in self.opt_keys: self._mom = self.opt.param_groups[0]['momentum']
        if 'alpha' in self.opt_keys: self._beta = self.opt.param_groups[0]['alpha']
        if 'betas' in self.opt_keys: self._mom,self._beta = self.opt.param_groups[0]['betas']
        if 'weight_decay' in self.opt_keys: self._wd = self.opt.param_groups[0]['weight_decay']

    def set_val(self, key:str, val:Any):
        "Set parameter on wrapped optimizer"
        for pg in self.opt.param_groups: pg[key] = val
        return val

class Callback():
    "Base class for callbacks that want to record values, dynamically change learner params, etc"
    def on_train_begin(self, **kwargs:Any)->None:
        "To initialize constants in the callback."
        pass
    def on_epoch_begin(self, **kwargs:Any)->None:
        "At the beginning of each epoch"
        pass
    def on_batch_begin(self, **kwargs:Any)->None:
        """To set HP before the step is done.
           Returns xb, yb (which can allow us to modify the input at that step if needed)"""
        pass
    def on_loss_begin(self, **kwargs:Any)->None:
        """Called after the forward pass but before the loss has been computed.
           Returns the output (which can allow us to modify it)"""
        pass
    def on_backward_begin(self, **kwargs:Any)->None:
        """Called after the forward pass and the loss has been computed, but before the back propagation.
           Returns the loss (which can allow us to modify it, for instance for reg functions)"""
        pass
    def on_backward_end(self, **kwargs:Any)->None:
        """Called after the back propagation had been done (and the gradients computed) but before the step of the optimizer.
           Useful for true weight decay in AdamW"""
        pass
    def on_step_end(self, **kwargs:Any)->None:
        "Called after the step of the optimizer but before the gradients are zeroed (not sure this one is useful)"
        pass
    def on_batch_end(self, **kwargs:Any)->None:
        "Called at the end of the batch"
        pass
    def on_epoch_end(self, **kwargs:Any)->bool:
        "Called at the end of an epoch"
        return False
    def on_train_end(self, **kwargs:Any)->None:
        "Useful for cleaning up things and saving files/models"
        pass

class SmoothenValue():
    "Creates a smooth moving average for a value (loss, etc)"
    def __init__(self, beta:float)->None:
        "Create smoother for value, beta should be 0<beta<1"
        self.beta,self.n,self.mov_avg = beta,0,0

    def add_value(self, val:float)->None:
        "Add current value to calculate updated smoothed value "
        self.n += 1
        self.mov_avg = self.beta * self.mov_avg + (1 - self.beta) * val
        self.smooth = self.mov_avg / (1 - self.beta ** self.n)

TensorOrNumber = Union[Tensor,Number]
CallbackList = Collection[Callback]
MetricsList = Collection[TensorOrNumber]
TensorOrNumList = Collection[TensorOrNumber]
MetricFunc = Callable[[Tensor,Tensor],TensorOrNumber]
MetricFuncList = Collection[MetricFunc]


def _get_init_state(): return {'epoch':0, 'iteration':0, 'num_batch':0}

@dataclass
class CallbackHandler():
    "Manages all of the registered callback objects, beta is for smoothing loss"
    callbacks:CallbackList
    beta:float=0.98

    def __post_init__(self)->None:
        "InitInitializeitialize smoother and learning stats"
        self.smoothener = SmoothenValue(self.beta)
        self.state_dict:Dict[str,Union[int,float,Tensor]]=_get_init_state()

    def __call__(self, cb_name, **kwargs)->None:
        "Call through to all of the callback handlers"
        return [getattr(cb, f'on_{cb_name}')(**self.state_dict, **kwargs) for cb in self.callbacks]

    def on_train_begin(self, epochs:int, pbar:PBar, metrics:MetricFuncList)->None:
        "About to start learning"
        self.state_dict = _get_init_state()
        self.state_dict['n_epochs'],self.state_dict['pbar'],self.state_dict['metrics'] = epochs,pbar,metrics
        self('train_begin')

    def on_epoch_begin(self)->None:
        "Handle new epoch"
        self.state_dict['num_batch'] = 0
        self('epoch_begin')

    def on_batch_begin(self, xb:Tensor, yb:Tensor)->None:
        "Handle new batch `xb`,`yb`"
        self.state_dict['last_input'], self.state_dict['last_target'] = xb, yb
        for cb in self.callbacks:
            a = cb.on_batch_begin(**self.state_dict)
            if a is not None: self.state_dict['last_input'], self.state_dict['last_target'] = a
        return self.state_dict['last_input'], self.state_dict['last_target']

    def on_loss_begin(self, out:Tensor)->None:
        "Handle start of loss calculation with model output `out`"
        self.state_dict['last_output'] = out
        for cb in self.callbacks:
            a = cb.on_loss_begin(**self.state_dict)
            if a is not None: self.state_dict['last_output'] = a
        return self.state_dict['last_output']

    def on_backward_begin(self, loss:Tensor)->None:
        "Handle gradient calculation on `loss`"
        self.smoothener.add_value(loss.detach())
        self.state_dict['last_loss'], self.state_dict['smooth_loss'] = loss, self.smoothener.smooth
        for cb in self.callbacks:
            a = cb.on_backward_begin(**self.state_dict)
            if a is not None: self.state_dict['last_loss'] = a
        return self.state_dict['last_loss']

    def on_backward_end(self)->None:
        "Handle end of gradient calc"
        self('backward_end')
    def on_step_end(self)->None:
        "Handle end of optimization step"
        self('step_end')

    def on_batch_end(self, loss:Tensor)->None:
        "Handle end of processing one batch with `loss`"
        self.state_dict['last_loss'] = loss
        stop = np.any(self('batch_end'))
        self.state_dict['iteration'] += 1
        self.state_dict['num_batch'] += 1
        return stop

    def on_epoch_end(self, val_metrics:MetricsList)->bool:
        "Epoch is done, process `val_metrics`"
        self.state_dict['last_metrics'] = val_metrics
        stop = np.any(self('epoch_end'))
        self.state_dict['epoch'] += 1
        return stop

    def on_train_end(self, exception:Union[bool,Exception])->None:
        "Handle end of training, `exception` is an `Exception` or False if no exceptions during training"
        self('train_end', exception=exception)


OptMetrics = Optional[Collection[Any]]
OptLossFunc = Optional[LossFunction]
OptCallbackHandler = Optional[CallbackHandler]
OptOptimizer = Optional[optim.Optimizer]
OptCallbackList = Optional[CallbackList]


def loss_batch(model:Model, xb:Tensor, yb:Tensor, loss_fn:OptLossFunc=None,
               opt:OptOptimizer=None, cb_handler:OptCallbackHandler=None,
               metrics:OptMetrics=None)->Tuple[Union[Tensor,int,float,str]]:
    "Calculate loss for a batch, calculate metrics, call out to callbacks as necessary"
    if cb_handler is None: cb_handler = CallbackHandler([])
    if not is_listy(xb): xb = [xb]
    if not is_listy(yb): yb = [yb]
    out = model(*xb)
    out = cb_handler.on_loss_begin(out)
    if not loss_fn: return out.detach(),yb[0].detach()
    loss = loss_fn(out, *yb)
    mets = [f(out,*yb).detach().cpu() for f in metrics] if metrics is not None else []

    if opt is not None:
        loss = cb_handler.on_backward_begin(loss)
        loss.backward()
        cb_handler.on_backward_end()
        opt.step()
        cb_handler.on_step_end()
        opt.zero_grad()

    return (loss.detach().cpu(),) + tuple(mets) + (yb[0].shape[0],)


def validate(model:Model, dl:DataLoader, loss_fn:OptLossFunc=None,
             metrics:OptMetrics=None, cb_handler:OptCallbackHandler=None,
             pbar:Optional[PBar]=None)->Iterator[Tuple[Union[Tensor,int],...]]:
    "Calculate loss and metrics for the validation set"
    model.eval()
    with torch.no_grad():
        return zip(*[loss_batch(model, xb, yb, loss_fn, cb_handler=cb_handler, metrics=metrics)
                       for xb,yb in progress_bar(dl, parent=pbar)])

def fit(epochs:int, model:Model, loss_fn:LossFunction, opt:optim.Optimizer,
        data:DataBunch, callbacks:OptCallbackList=None, metrics:OptMetrics=None)->None:
    "Fit the `model` on `data` and learn using `loss` and `opt`"
    cb_handler = CallbackHandler(callbacks)
    pbar = master_bar(range(epochs))
    cb_handler.on_train_begin(epochs, pbar=pbar, metrics=metrics)

    exception=False
    try:
        for epoch in pbar:
            model.train()
            cb_handler.on_epoch_begin()

            for xb,yb in progress_bar(data.train_dl, parent=pbar):
                xb, yb = cb_handler.on_batch_begin(xb, yb)
                loss,_ = loss_batch(model, xb, yb, loss_fn, opt, cb_handler)
                if cb_handler.on_batch_end(loss): break

            if hasattr(data,'valid_dl') and data.valid_dl is not None:
                *val_metrics,nums = validate(model, data.valid_dl, loss_fn=loss_fn,
                                             cb_handler=cb_handler, metrics=metrics,pbar=pbar)
                nums = np.array(nums, dtype=np.float32)
                val_metrics = [(torch.stack(val).cpu().numpy() * nums).sum() / nums.sum()
                               for val in val_metrics]

            else: val_metrics=None
            if cb_handler.on_epoch_end(val_metrics): break
    except Exception as e:
        exception = e
        raise e
    finally: cb_handler.on_train_end(exception)

_camel_re1 = re.compile('(.)([A-Z][a-z]+)')
_camel_re2 = re.compile('([a-z0-9])([A-Z])')
def camel2snake(name:str)->str:
    s1 = re.sub(_camel_re1, r'\1_\2', name)
    return re.sub(_camel_re2, r'\1_\2', s1).lower()

@dataclass
class LearnerCallback(Callback):
    "Base class for creating callbacks for the `Learner`"
    learn: Learner
    def __post_init__(self):
        if self.cb_name: setattr(self.learn, self.cb_name, self)

    @property
    def cb_name(self): return camel2snake(self.__class__.__name__)

class Recorder(LearnerCallback):
    "A `LearnerCallback` that records epoch,loss,opt and metric data during training"
    def __init__(self, learn:Learner):
        super().__init__(learn)
        self.opt = self.learn.opt
        self.train_dl = self.learn.data.train_dl

    def on_train_begin(self, pbar:PBar, metrics:MetricFuncList, **kwargs:Any)->None:
        "Initialize recording status at beginning of training"
        self.pbar = pbar
        self.names = ['epoch', 'train loss', 'valid loss'] + [fn.__name__ for fn in metrics]
        self.pbar.write('  '.join(self.names))
        self.losses,self.val_losses,self.lrs,self.moms,self.metrics,self.nb_batches = [],[],[],[],[],[]

    def on_batch_begin(self, **kwargs:Any)->None:
        "Record learning rate and momentum at beginning of batch"
        self.lrs.append(self.opt.lr)
        self.moms.append(self.opt.mom)

    def on_backward_begin(self, smooth_loss:Tensor, **kwargs:Any)->None:
        "Record the loss before any other callback has a chance to modify it."
        self.losses.append(smooth_loss)
        if self.pbar is not None and hasattr(self.pbar,'child'):
            self.pbar.child.comment = f'{smooth_loss:.4f}'

    def on_epoch_end(self, epoch:int, num_batch:int, smooth_loss:Tensor,
                     last_metrics=MetricsList, **kwargs:Any)->bool:
        "Save epoch info: num_batch, smooth_loss, metrics"
        self.nb_batches.append(num_batch)
        if last_metrics is not None:
            self.val_losses.append(last_metrics[0])
            if len(last_metrics) > 1: self.metrics.append(last_metrics[1:])
            self.format_stats([epoch, smooth_loss] + last_metrics)
        else:  self.format_stats([epoch, smooth_loss])
        return False

    def format_stats(self, stats:TensorOrNumList)->None:
        str_stats = []
        for name,stat in zip(self.names,stats):
            t = str(stat) if isinstance(stat, int) else f'{stat:.6f}'
            t += ' ' * (len(name) - len(t))
            str_stats.append(t)
        self.pbar.write('  '.join(str_stats))

    def plot_lr(self, show_moms=False)->None:
        "Plot learning rate, `show_moms` to include momentum"
        iterations = list(range(len(self.lrs)))
        if show_moms:
            _, axs = plt.subplots(1,2, figsize=(12,4))
            axs[0].plot(iterations, self.lrs)
            axs[1].plot(iterations, self.moms)
        else: plt.plot(iterations, self.lrs)

    def plot(self, skip_start:int=10, skip_end:int=5)->None:
        "Plot learning rate and losses, trimmed between `skip_start` and `skip_end`"
        lrs = self.lrs[skip_start:-skip_end] if skip_end > 0 else self.lrs[skip_start:]
        losses = self.losses[skip_start:-skip_end] if skip_end > 0 else self.losses[skip_start:]
        _, ax = plt.subplots(1,1)
        ax.plot(lrs, losses)
        ax.set_xscale('log')

    def plot_losses(self)->None:
        "Plot training and validation losses"
        _, ax = plt.subplots(1,1)
        iterations = list(range(len(self.losses)))
        ax.plot(iterations, self.losses)
        val_iter = self.nb_batches
        val_iter = np.cumsum(val_iter)
        ax.plot(val_iter, self.val_losses)

    def plot_metrics(self)->None:
        "Plot metrics collected during training"
        assert len(self.metrics) != 0, "There are no metrics to plot."
        _, axes = plt.subplots(len(self.metrics[0]),1,figsize=(6, 4*len(self.metrics[0])))
        val_iter = self.nb_batches
        val_iter = np.cumsum(val_iter)
        axes = axes.flatten() if len(self.metrics[0]) != 1 else [axes]
        for i, ax in enumerate(axes):
            values = [met[i] for met in self.metrics]
            ax.plot(val_iter, values)

def accuracy(out:Tensor, yb:Tensor)->TensorOrNumber:
    "Calculate percentage of 1-hot `out` correctly predicted in `yb`"
    preds = torch.argmax(out, dim=1)
    return (preds==yb).float().mean()

AdamW = partial(optim.Adam, betas=(0.9,0.99))

@dataclass
class Learner():
    """Trains `module` with `data` using `loss_fn` and `opt_fn`, collects `metrics` along the way
       `true_wd` along with `wd` turn on weight decay, `path` specifies where models are stored
       `callback_fns` is used to add custom callbacks beyond Recorder which is added by default"""
    data:DataBunch
    model:nn.Module
    opt_fn:Callable=AdamW
    loss_fn:Callable=F.cross_entropy
    metrics:Collection[Callable]=None
    true_wd:bool=True
    wd:Floats=1e-2
    path:str = 'models'
    callback_fns:Collection[Callable]=None
    callbacks:Collection[Callback]=field(default_factory=list)
    def __post_init__(self):
        "Sets up internal learner variables"
        self.path = Path(self.path)
        self.metrics=listify(self.metrics)
        self.path.mkdir(parents=True, exist_ok=True)
        self.model = self.model.to(self.data.device)
        self.callbacks = listify(self.callbacks)
        self.callback_fns = [Recorder] + listify(self.callback_fns)

    def fit(self, epochs:int, lr:Optional[Floats], wd:Optional[Floats]=None, callbacks:OptCallbackList=None)->None:
        "Fit the model in this learner with `lr` learning rate and `wd` weight decay"
        if wd is None: wd = self.wd
        self.create_opt(lr, wd)
        callbacks = [cb(self) for cb in self.callback_fns] + listify(callbacks)
        fit(epochs, self.model, self.loss_fn, self.opt, self.data, metrics=self.metrics,
            callbacks=self.callbacks+callbacks)

    def create_opt(self, lr:Floats, wd:Floats=0.)->None:
        "Binds a new optimizer each time `fit` is called with `lr` learning rate and `wd` weight decay"
        self.opt = OptimWrapper(self.opt_fn(self.model.parameters(),lr))

    def save(self, name:PathOrStr)->None:
        "Save the model bound to this learner in the `path` folder with `name`"
        torch.save(self.model.state_dict(), self.path/f'{name}.pth')
    def load(self, name:PathOrStr):
        "Load the model bound to this learner with the `name` model params in the `path` folder"
        self.model.load_state_dict(torch.load(self.path/f'{name}.pth'))


AnnealFunc = Callable[[Number,Number,float], Number]
def annealing_no(start:Number, end:Number, pct:float)->Number:
    "No annealing, always return `start`"
    return start
def annealing_linear(start:Number, end:Number, pct:float)->Number:
    "Linearly anneal from `start` to `end` as pct goes from 0.0 to 1.0"
    return start + pct * (end-start)
def annealing_exp(start:Number, end:Number, pct:float)->Number:
    "Exponentially anneal from `start` to `end` as pct goes from 0.0 to 1.0"
    return start * (end/start) ** pct
def annealing_cos(start:Number, end:Number, pct:float)->Number:
    "Cosine anneal from `start` to `end` as pct goes from 0.0 to 1.0"
    cos_out = np.cos(np.pi * pct) + 1
    return end + (start-end)/2 * cos_out

def do_annealing_poly(start:Number, end:Number, pct:float, degree:Number)->Number:
    "Helper function for `anneal_poly`"
    return end + (start-end) * (1-pct)**degree
def annealing_poly(degree:Number)->Number:
    "Anneal polynomically from `start` to `end` as pct goes from 0.0 to 1.0"
    return functools.partial(do_annealing_poly, degree=degree)

def is_tuple(x:Any)->bool: return isinstance(x, tuple)
StartOptEnd=Union[float,Tuple[float,float]]
class Stepper():
    "Used to \"step\" from start,end (`vals`) over `n_iter` iterations on a schedule defined by `func` (defaults to linear)"
    def __init__(self, vals:StartOptEnd, n_iter:int, func:Optional[AnnealFunc]=None):
        self.start,self.end = (vals[0],vals[1]) if is_tuple(vals) else (vals,0)
        self.n_iter = n_iter
        if func is None: self.func = annealing_linear if is_tuple(vals) else annealing_no
        else:          self.func = func
        self.n = 0

    def step(self)->Number:
        "Return next value along annealed schedule"
        self.n += 1
        return self.func(self.start, self.end, self.n/self.n_iter)

    @property
    def is_done(self)->bool:
        "Schedule completed"
        return self.n >= self.n_iter

@dataclass
class OneCycleScheduler(Callback):
    "Manages 1-Cycle style traing as outlined in Leslie Smith's [paper](https://arxiv.org/pdf/1803.09820.pdf)"
    learn:Learner
    lr_max:float
    moms:Floats=(0.95,0.85)
    div_factor:float=25.
    pct_start:float=0.5

    def __post_init__(self): self.moms=tuple(listify(self.moms,2))

    def steps(self, *steps_cfg:StartOptEnd):
        "Build anneal schedule for all of the parameters"
        return [Stepper(step, n_iter, func=func)
                for (step,(n_iter,func)) in zip(steps_cfg, self.phases)]

    def on_train_begin(self, n_epochs:int, **kwargs:Any)->None:
        "Initialize our optimization params based on our annealing schedule"
        n = len(self.learn.data.train_dl) * n_epochs
        a1 = int(n * self.pct_start)
        a2 = n-a1
        self.phases = ((a1, annealing_linear), (a2, annealing_cos))
        low_lr = self.lr_max/self.div_factor
        self.lr_scheds = self.steps((low_lr, self.lr_max), (self.lr_max, low_lr/1e4))
        self.mom_scheds = self.steps(self.moms, (self.moms[1], self.moms[0]))
        self.opt = self.learn.opt
        self.opt.lr,self.opt.mom = self.lr_scheds[0].start,self.mom_scheds[0].start
        self.idx_s = 0

    def on_batch_end(self, **kwargs:Any)->None:
        "Take one step forward on the annealing schedule for the optim params"
        if self.idx_s >= len(self.lr_scheds): return Trrue
        self.opt.lr = self.lr_scheds[self.idx_s].step()
        self.opt.mom = self.mom_scheds[self.idx_s].step()
        # when the current schedule is complete we move onto the next
        # schedule. (in 1-cycle there are two schedules)
        if self.lr_scheds[self.idx_s].is_done:
            self.idx_s += 1

def one_cycle_scheduler(lr_max:float, **kwargs:Any)->OneCycleScheduler:
    return partial(OneCycleScheduler, lr_max=lr_max, **kwargs)

def fit_one_cycle(learn:Learner, cyc_len:int, max_lr:float, moms:Tuple[float,float]=(0.95,0.85),
                  div_factor:float=10., pct_start:float=0.5, wd:Optional[float]=None):
    "Fits a model following the 1cycle policy"
    cbs = [OneCycleScheduler(learn, max_lr, moms=moms, div_factor=div_factor,
                             pct_start=pct_start)]
    learn.fit(cyc_len, max_lr, wd=wd, callbacks=cbs)

@dataclass
class TrainingPhase():
    "Schedule lr,mom according to `lr_anneal` and `mom_anneal` across a `length` schedule"
    length:int
    lrs:Floats
    moms:Floats
    lr_anneal:Callable=None
    mom_anneal:Callable=None

    def __post_init__(self)->None:
        self.lr_step = Stepper(lrs, length, lr_anneal)
        self.mom_step = Stepper(moms, length, mom_anneal)

@dataclass
class GeneralScheduler(Callback):
    "Schedule multiple `TrainingPhase` for a `learner`"
    learn:Learner
    phases:Collection[TrainingPhase]

    def on_train_begin(self, n_epochs:int, **kwargs:Any)->None:
        "Initialize our lr and mom schedules for training"
        self.lr_scheds = [p.lr_step for p in self.phases]
        self.mom_scheds = [p.mom_step for p in self.phases]
        self.opt = self.learn.opt
        self.opt.lr,self.opt.mom = self.lr_scheds[0].start,self.mom_scheds[0].start
        self.idx_s = 0

    def on_batch_end(self, **kwargs:Any)->None:
        "Take a step in lr,mom sched, start next sched when current is complete"
        if self.idx_s >= len(self.lr_scheds): return True
        self.opt.lr = self.lr_scheds[self.idx_s].step()
        self.opt.mom = self.mom_scheds[self.idx_s].step()
        if self.lr_scheds[self.idx_s].is_done:
            self.idx_s += 1

class LRFinder(LearnerCallback):
    "Explore lr vs loss relationship for a learner"
    def __init__(self, learn:Learner, start_lr:float=1e-5, end_lr:float=10, num_it:int=200)->None:
        "Initialize schedule of learning rates"
        super().__init__(learn)
        self.data = learn.data
        self.sched = Stepper((start_lr, end_lr), num_it, annealing_exp)
        #To avoid validating if the train_dl has less than num_it batches, we put aside the valid_dl and remove it
        #during the call to fit.
        self.valid_dl = learn.data.valid_dl
        self.data.valid_dl = None

    def on_train_begin(self, **kwargs:Any)->None:
        "init optimizer and learn params"
        self.learn.save('tmp')
        self.opt = self.learn.opt
        self.opt.lr = self.sched.start
        self.stop,self.best_loss = False,0.

    def on_batch_end(self, iteration:int, smooth_loss:TensorOrNumber, **kwargs:Any)->None:
        "Determine if loss has runaway and we should stop"
        if iteration==0 or smooth_loss < self.best_loss: self.best_loss = smooth_loss
        self.opt.lr = self.sched.step()
        if self.sched.is_done or smooth_loss > 4*self.best_loss:
            #We use the smoothed loss to decide on the stopping since it's less shaky.
            self.stop=True
            return True

    def on_epoch_end(self, **kwargs:Any)->None:
        "Tell Learner if we need to stop"
        return self.stop

    def on_train_end(self, **kwargs:Any)->None:
        "Cleanup learn model weights disturbed during LRFind exploration"
        # restore the valid_dl we turned of on `__init__`
        self.data.valid_dl = self.valid_dl
        self.learn.load('tmp')

def lr_find(learn:Learner, start_lr:float=1e-5, end_lr:float=10, num_it:int=100, **kwargs:Any):
    "Explore lr from `start_lr` to `end_lr` over `num_it` iterations of `learn`"
    cb = LRFinder(learn, start_lr, end_lr, num_it)
    a = int(np.ceil(num_it/len(learn.data.train_dl)))
    learn.fit(a, start_lr, callbacks=[cb], **kwargs)

class ShowGraph(LearnerCallback):
    "Updates a graph of learner stats and metrics after each epoch"
    def on_epoch_end(self, n_epochs:int, last_metrics:MetricsList, **kwargs)->bool:
        "If we have metrics plot them in our pbar graph"
        if last_metrics is not None:
            rec = learn.recorder
            iters = list(range(len(rec.losses)))
            val_iter = np.array(rec.nb_batches).cumsum()
            x_bounds = (0, (n_epochs - len(rec.nb_batches)) * rec.nb_batches[-1] + len(rec.losses))
            y_bounds = (0, max((max(tensor(rec.losses)), max(tensor(rec.val_losses)))))
            rec.pbar.update_graph([(iters, rec.losses), (val_iter, rec.val_losses)], x_bounds, y_bounds)
            return False