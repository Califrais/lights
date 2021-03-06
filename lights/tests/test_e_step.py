# -*- coding: utf-8 -*-
# Author: Simon Bussy <simon.bussy@gmail.com>

import unittest
import numpy as np
from lights.tests.testing_data import CreateTestingData
from lights.model.e_step_functions import EstepFunctions


class Test(unittest.TestCase):
    """A class to test E_step functions
    """

    def setUp(self):
        data = CreateTestingData()
        alpha = data.fixed_effect_time_order
        theta, asso_functions = data.theta, data.asso_functions
        self.n_samples = data.n_samples
        self.S, self.n_MC = data.S, data.S.shape[0]
        self.E_func = EstepFunctions(data.X, data.T, data.T_u, data.delta,
                                     data.ext_feat, alpha, asso_functions,
                                     theta)
        self.ind_1, self.ind_2 = data.ind_1, data.ind_2
        self.data = data
        self.g5_0_1 = np.array(
            [[1, 2, 4, 0, 0, 0, 0, 0, 0, 0, 1, 4, 2, 2, 8 / 3],
             [1, 2, 4, 0, 0, 0, 0, 0, 0, 0, 1, 4, 2, 2, 8 / 3],
             [1, 2, 4, 0, 0, 0, 0, 0, 0, 0, 1, 4, 2, 2, 8 / 3]])
        self.g5_1_3 = np.array(
            [[1, 3, 9, 0, 0, 0, 0, 0, 0, 0, 1, 6, 3, 9 / 2, 9],
             [1, 3, 9, 0, 0, 0, 0, 0, 0, 0, 1, 6, 3, 9 / 2, 9],
             [1, 3, 9, 0, 0, 0, 0, 0, 0, 0, 1, 6, 3, 9 / 2, 9]])
        self.g6_0_1 = np.exp(49) * self.g5_0_1

    def test_g1(self):
        """Tests the g1 function
        """
        self.setUp()
        theta = self.data.theta
        beta_0, beta_1 = theta["beta_0"], theta["beta_1"]
        gamma_0, gamma_1 = theta["gamma_0"], theta["gamma_1"]
        g1 = self.E_func.g1(self.S, gamma_0, beta_0, gamma_1, beta_1, broadcast=False)
        g1_0_1 = np.exp(np.array([356/3, 335/3, 227/3, 275/3]))
        g1_1_3 = np.exp(np.array([147, 172.5, 145.5, 61.5]))
        np.testing.assert_almost_equal(np.log(g1[0, 0, :, 0]), np.log(g1_0_1))
        np.testing.assert_almost_equal(np.log(g1[0, 1, :, 1]), np.log(g1_1_3))

    def test_g2(self):
        """Tests the g2 function
        """
        self.setUp()
        theta = self.data.theta
        beta_0, beta_1 = theta["beta_0"], theta["beta_1"]
        gamma_0, gamma_1 = theta["gamma_0"], theta["gamma_1"]
        g2 = self.E_func.g2(self.S, gamma_0, beta_0, gamma_1, beta_1)
        # values of g2 at first group and first sample
        g2_0_1 = np.array([347/3, 326/3, 218/3, 266/3])
        # values of g2 at second group and second sample
        g2_1_3 = np.array([153 , 178.5, 151.5,  67.5])
        np.testing.assert_almost_equal(g2[0, 0], g2_0_1)
        np.testing.assert_almost_equal(g2[1, 1], g2_1_3)

    def test_Lambda_g(self):
        """Tests the Lambda_g function
        """
        self.setUp()
        tmp = np.arange(1, 49).reshape(3, 2, 4, 2)
        g1 = np.broadcast_to(tmp[..., None], tmp.shape + (2,)).swapaxes(1, -1)
        f = .02 * np.arange(1, 25).reshape(3, 2, 4)
        Lambda_g1 = self.E_func.Lambda_g(g1, f)
        Lambda_g1_ = np.array([[0.25, 0.65], [0.57, 1.61]])
        np.testing.assert_almost_equal(Lambda_g1[0, :, 0], Lambda_g1_)

    def test_Eg(self):
        """Tests the expection of g functions
        """
        self.setUp()
        tmp = np.arange(1, 49).reshape(3, 2, 4, 2)
        g1 = np.broadcast_to(tmp[..., None], tmp.shape + (2,)).swapaxes(1, -1)
        f = .02 * np.arange(1, 25).reshape(3, 2, 4)
        n_samples, n_MC, K = self.n_samples, self.n_MC, 2
        Lambda_1 = self.E_func.Lambda_g(np.ones(shape=(n_samples, K, n_MC)), f)
        pi_xi = 1 / (1 + np.exp(np.array([-3, -4, -6])))
        Eg1 = self.E_func.Eg(g1, Lambda_1, pi_xi, f)
        Eg1_ = np.array([4.396, 12.396])
        np.testing.assert_almost_equal(Eg1[0, 0], Eg1_, 3)

if __name__ == "main":
    unittest.main()
