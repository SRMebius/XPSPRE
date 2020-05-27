#!/usr/bin/env python
#coding:utf-8
'''@author: ZKY'''
 
import numpy as np

class Normalization():
    
    def __init__(self):
        pass
    
    def max(self):
        return np.max(self.df)
    
    def min(self):
        return np.min(self.df)
    
    def aver(self):
        return np.average(self.df)
    
    def std(self):
        return np.std(self.df)
    
    def method_1(self, df):
        '''Normalize to [0, 1]'''
        self.df = df
        df = (df - self.min()) / (self.max() - self.min())
        return df
    
    def method_2(self, df):
        '''Divided by Max'''
        self.df = df
        df = df / self.max()
        return df
    
    def method_3(self, df):
        '''Z scores (standardize to N(0, 1)) 要求原始数据的分布可以近似为高斯分布，否则归一化效果会比较差'''    
        self.df = df
        df = (df - self.min()) / self.std()
        return df
     
    def method_4(self, df, x1, x2):
        ''''Divide by custom'''
        cols = df.columns
        self.df = df[cols[1]]
        minium = self.min()
        self.df = df[(df[cols[0]] > x1) & (df[cols[0]] < x2)][cols[1]]
        df = (df[cols[1]] - minium) / (self.max() - minium)
        return df

    def method_5(self, df):
        '''sigmoid函数'''
        pass


