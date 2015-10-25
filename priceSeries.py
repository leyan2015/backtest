import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn
import json
import os

import datetime as dt
from workingDay import workingDay
from parameter import parameters
from yahoo_retriever import get_data



class priceSeries(object):
    '''
    NOT A PRODUCTION VERSION
    
    TODO
    
    1. generate group price - DONE
    2. compare dates with working Day, if price missing, request it again (to be done maybe in 2nd phase) ( potentially daily scheduler, and health check)
    
    '''
    
    def __init__ (self, symbol, basket=False, spec=None):
        if basket==False:
            self.symbol = symbol
            csvFile = './price_data/day/'+symbol+'.csv'
            if os.path.isfile(csvFile) == False:
                get_data(self.symbol)
            self.df = pd.read_csv(csvFile)
        else:
            if spec is None:
                print "for basket security prices, spec(trade) name must be provided"
                raise 
            p = parameters(spec)
            basketParam = p.get(['security', 'weight'],basket, 'security')
            self.symbol = basket
            
            for index, item in enumerate(basketParam):
                symbol = item[0]
                weight = float(item[1])
                csvFile = './price_data/day/'+symbol+'.csv'
                if os.path.isfile(csvFile) == False:
                    print "getting symbol prices online", symbol
                    get_data(symbol)

                tempdf = pd.read_csv(csvFile)
                if index == 0:
                    self.df = pd.DataFrame(data=0, index=tempdf.index, columns=tempdf.columns)
                    self.df['Date'] = tempdf['Date']
                beginningPrice = tempdf.tail(1)['Adj Close'].values[0]
                tempdf['Adj Close'] /= beginningPrice / 100.
                self.df[['Open','High','Low','Close','Volume','Adj Close']] += tempdf[['Open','High','Low','Close','Volume','Adj Close']]*weight  # times weights
            self.df.dropna(inplace=True)  
                #Question, should I round before the sum or after?
                #self.df[['Open','High','Low','Close','Volume','Adj Close']].apply(np.round(2))
            
        self.df.sort('Date', inplace=True)
        self.df.reset_index(drop=True, inplace=True)
    
        
    def dailyReturns(self, start=dt.datetime(2012, 1, 3).date(), outputFormat = 'logReturn'):

        df = self.df
        index = df[df.Date>=str(start)][0:1].index[0]
        df = df[max(index-1,0):]
        df.reset_index(drop=True, inplace=True)

        openPrice = df[0:1]['Adj Close'].values[0] # first price in the time series
        #df['return'] = np.log( df['Adj Close'] / df['Adj Close'].shift() )  # log return

        df['return'] = df['Adj Close'] / df['Adj Close'].shift() -1  # return
        df['cumulative'] = ( df['Adj Close']/openPrice  )-1  # cumulative Return
        self.dailyDF = df[1:]
        
        # cumulative    np.exp(np.cumsum(df['return'].values[1:]), dtype=np.float64)-1
        if outputFormat == 'logReturn':
            return self.dailyDF['return'].values
        elif outputFormat == 'dataFrame':
            return self.dailyDF
        elif outputFormat == 'cumulative':
            return self.dailyDF['cumulative'].values
        else:
            pass
    
    
    def weeklyReturn(self, start=dt.datetime(2012, 1, 3).date(), outputFormat = 'logReturn'):
        self.dailyReturns( start, outputFormat=None)
        workingDayObj = workingDay()
        workingDayDF = workingDayObj.generateWorkingDay(outputFormat='dataFrame')
        weeklyDF = pd.merge(workingDayDF, self.dailyDF, left_on='days', right_on='Date')
        weeklyDF=weeklyDF.groupby('lastDayinWeek').sum()
        
        weeklyDF=pd.DataFrame(weeklyDF['return'].apply(lambda(x): np.exp(x)-1))
        return weeklyDF