import numpy as np
from sklearn.model_selection import KFold
from lights.inference import QNMCEM


def cross_validate(X, Y, T, delta, n_folds=10, eta=0.1,
                   adaptative_grid_el=True, grid_size=30,
                   grid_params=[(0, 0, 0)], shuffle=True,
                   verbose=True, metric='C-index', tol=1e-5, warm_start=True,
                   eta_elastic_net=.1, eta_sp_gp_l1=.1):
    """Apply n_folds randomized search cross-validation using the given
    data, to select the best penalization hyper-parameters

    Parameters
    ----------
    X : `np.ndarray`, shape=(n_samples, n_time_indep_features)
        The time-independent features matrix

    Y : `pandas.DataFrame`, shape=(n_samples, n_long_features)
        The simulated longitudinal data. Each element of the dataframe is
        a pandas.Series

    T : `np.ndarray`, shape=(n_samples,)
        Censored times of the event of interest

    delta : `np.ndarray`, shape=(n_samples,)
        Censoring indicator

    n_folds : `int`, default=10
        Number of folds. Must be at least 2.

    eta : `float`, default=0.1
        The ElasticNet mixing parameter, with 0 <= eta <= 1.
        For eta = 0 this is ridge (L2) regularization
        For eta = 1 this is lasso (L1) regularization
        For 0 < eta < 1, the regularization is a linear combination
        of L1 and L2

    adaptative_grid_el : `bool`, default=True
        If `True`, adapt the ElasticNet strength parameter grid using the
        KKT conditions

    grid_size : `int`, default=30
        Grid size if adaptative_grid_el=`True`

    grid_params : list of tuples, default=[(0, 0, 0)]
        Grid of strength parameters to be run through, if
        adaptative_grid_el=`False`

    shuffle : `bool`, default=True
        Whether to shuffle the data before splitting into batches

    verbose : `bool`, default=True
        If `True`, we verbose things, otherwise the solver does not
        print anything (but records information in history anyway)

    metric : 'log_lik', 'C-index', default='C-index'
        Either computes log-likelihood or C-index
    """
    n_samples = T.shape[0]
    cv = KFold(n_splits=n_folds, shuffle=shuffle)

    if adaptative_grid_el:
        # from KKT conditions
        gamma_max = 1. / np.log(10.) * np.log(
            1. / (1. - eta_elastic_net) * (.5 / n_samples)
            * np.absolute(X).sum(axis=0).max())

        # TODO: Update KKT conditions for all hyper-params
        grid_elastic_net = np.logspace(gamma_max - 4, gamma_max, grid_size)

    learners = [
        QNMCEM(verbose=False, tol=tol, warm_start=warm_start)
        for _ in range(n_folds)
    ]

    n_grid = len(grid_params)
    scores = np.empty((n_grid, n_folds))
    if verbose is not None:
        verbose = verbose
    for idx, params in enumerate(grid_params):
        if verbose:
            print("Testing l_pen_EN=%.2e, l_pen_SGL_beta=%.2e, "
                  "l_pen_SGL_gamma=%.2e" % params, "on fold ", end="")
        for n_fold, (idx_train, idx_test) in enumerate(cv.split(X)):
            if verbose:
                print(" " + str(n_fold), end="")
            X_train, X_test = X[idx_train], X[idx_test]
            T_train, T_test = Y[idx_train], T[idx_test]
            delta_train, delta_test = delta[idx_train], delta[idx_test]
            learner = learners[n_fold]
            learner.l_pen_EN, l_pen_SGL_beta, l_pen_SGL_gamma = params
            learner.fit(X_train, T_train, delta_train)
            scores[idx, n_fold] = learner.score(
                X_test, T_test, delta_test, metric)
        if verbose:
            print(": avg_score=%.2e" % scores[idx, :].mean())

    avg_scores = scores.mean(1)
    std_scores = scores.std(1)
    idx_best = avg_scores.argmax()
    params_best = grid_params[idx_best]
