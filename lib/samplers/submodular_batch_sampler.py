from torch.utils.data.sampler import Sampler, SequentialSampler, RandomSampler
from torch._six import int_classes as _int_classes
import time

from submodular import SubModSampler
from lib.utils import log
from lib.config import cfg
import numpy as np
from operator import itemgetter


class SubmodularBatchSampler(Sampler):
    """
    Returns back a minibatch, which is sampled such that the SubModular Objective is maximised.

    (adapted from: https://github.com/pytorch/pytorch/blob/master/torch/utils/data/sampler.py#L126)
    """

    def __init__(self, model, data_source, batch_size, sampler=None, drop_last=False):
        if sampler is None:
            sampler = RandomSampler(data_source)

        if not isinstance(sampler, Sampler):
            raise ValueError("sampler should be an instance of "
                             "torch.utils.data.Sampler, but got sampler={}"
                             .format(sampler))
        if not isinstance(batch_size, _int_classes) or isinstance(batch_size, bool) or \
                batch_size <= 0:
            raise ValueError("batch_size should be a positive integeral value, "
                             "but got batch_size={}".format(batch_size))
        if not isinstance(drop_last, bool):
            raise ValueError("drop_last should be a boolean value, but got "
                             "drop_last={}".format(drop_last))

        self.sampler = sampler
        self.dataset = data_source
        self.batch_size = batch_size
        self.drop_last = drop_last
        self.override_submodular_sampling = cfg.override_submodular_sampling
        self.submodular_sampler = SubModSampler(model, data_source, self.batch_size, cfg.ltl_log_ep)
        # TODO: Handle Replacement Strategy

    def __iter__(self):
        batch = []
        if self.override_submodular_sampling:
            for idx in self.sampler:
                batch.append(idx)
                if len(batch) == self.batch_size:
                    yield np.take(self.dataset.data, batch, axis=0), np.take(self.dataset.targets, batch, axis=0)
                    batch = []
        elif(cfg.use_iter):
            batch = self.submodular_sampler.get_subset()
            a = self.dataset.data
            b = self.dataset.targets
            yield np.take(self.dataset.data, batch, axis=0), np.take(self.dataset.targets, batch, axis=0)
        else:
            #r = np.random.random()
            r=1
            n_batches = int(len(self.sampler)*r) // self.batch_size
            log("Number in iterations in this epoch are {0}".format(n_batches))
            for i in range(n_batches):
                t_stamp = time.time()
                batch = self.submodular_sampler.get_subset()
                log('Fetched {0} of {1} in {2} seconds.'.format(i, len(self.sampler) // self.batch_size, time.time()-t_stamp))
                yield np.take(self.dataset.data, batch, axis=0), np.take(self.dataset.targets, batch, axis=0)

        if len(batch) > 0 and not self.drop_last:
            yield batch

    def __len__(self):
        if self.drop_last:
            return len(self.sampler) // self.batch_size
        else:
            return (len(self.sampler) + self.batch_size - 1) // self.batch_size
