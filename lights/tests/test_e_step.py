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
        g1 = self.E_func.g1(self.S, broadcast=False)
        g1_0_1 = np.exp(np.array([49, 56, 29, 4]))
        g1_1_3 = np.exp(np.array([55, 46, 76, 25.5]))
        np.testing.assert_almost_equal(g1[0, 0, :, 0], g1_0_1)
        np.testing.assert_almost_equal(g1[0, 1, :, 1], g1_1_3)

    def test_g2(self):
        """Tests the g2 function
        """
        self.setUp()
        g2 = self.E_func.g2(self.S, broadcast=False)
        # values of g2 at first group and first sample
        g2_0_1 = np.array([46, 53, 26, 1])
        # values of g2 at second group and second sample
        g2_1_3 = np.array([61, 52, 82, 31.5])
        np.testing.assert_almost_equal(g2[0, 0], g2_0_1)
        np.testing.assert_almost_equal(g2[1, 1], g2_1_3)

    def test_g5(self):
        """Tests the g5 function
        """
        self.setUp()
        g5 = self.E_func.g5(self.S, False)
        np.testing.assert_almost_equal(g5[0, 0, 0], self.g5_0_1)
        np.testing.assert_almost_equal(g5[1, 0, 1], self.g5_1_3)

    def test_g6(self):
        """Tests the g6 function
        """
        self.setUp()
        g6 = self.E_func.g6(self.S)
        np.testing.assert_almost_equal(g6[0, 0, 0, 0, :, :, 0], self.g6_0_1)

    def test_g7(self):
        """Tests the g7 function
        """
        self.setUp()
        g7 = self.E_func.g7(self.S, broadcast=False)
        g7_0_1 = np.array(
            [22, 1, 2, 16, 20, 16, 3, 2, 12, 40 / 3, 10, 3, 3, 2, 40 / 3])
        np.testing.assert_almost_equal(g7[0, 0, 0], g7_0_1)

    def test_g8(self):
        """Tests the g8 function
        """
        self.setUp()
        g8 = self.E_func.g8(self.S)
        g8_0_1 = np.exp(49) * np.array([22, 1, 2, 16, 20, 16, 3, 2, 12, 40 / 3,
                                        10, 3, 3, 2, 40 / 3])
        np.testing.assert_almost_equal(g8[0, 0, 0, 0, :, 0], g8_0_1)

    def test_g9(self):
        """Tests the g9 function
        """
        self.setUp()
        g9 = self.E_func.g9(self.S)
        # values of g2 at first group and first sample
        g9_0_1 = np.array([-1019, -260])
        np.testing.assert_almost_equal(g9[0, 0, 0], g9_0_1)

    def test_Lambda_g(self):
        """Tests the Lambda_g function
        """
        self.setUp()
        g8 = np.arange(1, 1441).reshape((3, 2, 4, 2, 15, 2))
        f = 0.2*np.ones((3, 2, 4))
        Lambda_g8 = self.E_func.Lambda_g(g8, f)
        Lambda_g8_ = np.array([[18.2, 18.4], [18.6, 18.8], [19, 19.2],
                          [19.4, 19.6], [19.8, 20], [20.2, 20.4],
                          [20.6, 20.8], [21, 21.2], [21.4, 21.6],
                          [21.8, 22], [22.2, 22.4], [22.6, 22.8],
                          [23, 23.2], [23.4, 23.6], [23.8, 24]])
        np.testing.assert_almost_equal(Lambda_g8[0, 0, 0], Lambda_g8_)

    def test_Eg(self):
        """Tests the expection of g functions
        """
        self.setUp()
        g8 = np.arange(1, 1441).reshape((3, 2, 4, 2, 15, 2))
        f = np.ones((3, 2, 4))
        n_samples, n_MC, K = self.n_samples, self.n_MC, 2
        Lambda_1 = self.E_func.Lambda_g(np.ones(shape=(n_samples, K, n_MC)), f)
        pi_xi = 1 / (1 + np.exp(np.array([-3, -4, -6])))
        Eg8 = self.E_func.Eg(g8, Lambda_1, pi_xi, f)
        Eg8_ = np.array([319.61779044, 321.61779044, 323.61779044,
                          325.61779044, 327.61779044, 329.61779044,
                          331.61779044, 333.61779044, 335.61779044,
                          337.61779044, 339.61779044, 341.61779044,
                          343.61779044, 345.61779044, 347.61779044])
        np.testing.assert_almost_equal(Eg8[0, 0, :, 0], Eg8_)

if __name__ == "main":
    unittest.main()
