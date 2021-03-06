"""Train a reduced version of the VGGNet network for 100 epochs.

It relies on the NetBenchmarking class from the NasGym. Similarly to
scripts/experiments-evaluation/network_evaluation.py, the network is trained
for 100 epochs using exponential decay (for fairness). The final accuracy is
printed.
"""

import math
import time
from datetime import datetime
import pandas as pd
import nasgym.utl.configreader as cr
from nasgym import nas_logger
from nasgym import CONFIG_INI
from nasgym.net_ops.net_benchmark import NetBenchmarking
from nasgym.envs.factories import DatasetHandlerFactory
from nasgym.envs.factories import TrainerFactory


if __name__ == '__main__':

    n_epochs = 100
    dataset_handler = DatasetHandlerFactory.get_handler("meta-dataset")
    composed_id = "vgg19_{d}".format(d=dataset_handler.current_dataset_name())

    try:
        log_path = CONFIG_INI[cr.SEC_DEFAULT][cr.PROP_LOGPATH]
    except KeyError:
        log_path = "workspace"

    log_trainer_dir = "{lp}/trainer-{h}".format(lp=log_path, h=composed_id)

    batch_size, decay_steps, beta1, beta2, epsilon, fcl_units, dropout_rate, \
        split_prop = TrainerFactory._load_default_trainer_attributes()

    trainset_length = math.floor(
        dataset_handler.current_n_observations()*(1. - split_prop)
    )
    evaluator = NetBenchmarking(
        input_shape=dataset_handler.current_shape(),
        n_classes=dataset_handler.current_n_classes(),
        batch_size=batch_size,
        log_path=log_trainer_dir,
        variable_scope="cnn-{h}".format(h=composed_id),
        n_epochs=n_epochs,
        op_beta1=0.9,
        op_beta2=0.999,
        op_epsilon=10e-08,
        dropout_rate=0.4,
        n_obs_train=trainset_length
    )

    train_features, train_labels = None, None
    val_features, val_labels = None, None

    def custom_train_input_fn():
        return dataset_handler.current_train_set()

    def custom_eval_input_fn():
        return dataset_handler.current_validation_set()

    train_input_fn = custom_train_input_fn
    eval_input_fn = custom_eval_input_fn

    nas_logger.debug(
        "Training architecture %s for %d epochs", composed_id, n_epochs
    )

    ev_results = pd.DataFrame(columns=["epoch", "test_accuracy"])

    start_time = time.time()
    for epoch in range(n_epochs):
        nas_logger.info("Running epoch %d", epoch + 1)
        evaluator.train(
            train_data=train_features,
            train_labels=train_labels,
            train_input_fn=train_input_fn,
            n_epochs=1  # As specified by BlockQNN
        )

        nas_logger.debug("Evaluating architecture %s", composed_id)
        res = evaluator.evaluate(
            eval_data=val_features,
            eval_labels=val_labels,
            eval_input_fn=eval_input_fn
        )

        accuracy = res['accuracy']*100
        ev_results = ev_results.append(
            {
                'epoch': epoch + 1,
                'test_accuracy': accuracy
            },
            ignore_index=True
        )
    end_time = time.time()

    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y%m%d%H%M%S%f")
    ev_res_path = "{log}/{cid}-{ep}-{time}.csv".format(
        log=log_path,
        cid=composed_id,
        ep=n_epochs,
        time=timestamp_str
    )

    outfile = open(ev_res_path, 'w')
    ev_results.to_csv(outfile)
    outfile.close()

    nas_logger.debug(
        "Train-evaluation procedure finished for architecture %s",
        composed_id
    )

    nas_logger.info("Final accuracy is %f", accuracy)
    nas_logger.info("Training-evaluation time %f", (end_time - start_time))
