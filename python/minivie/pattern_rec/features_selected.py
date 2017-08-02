#recieves commands from web interface and creates a list of class instances with each selected feature

import pattern_rec as pr
import logging
import threading
import time

class Features_selected(object):

    def __init__(self, vie):

        self.vie = vie
        self.features_dict = {"mav" : True, "curve_len" : True, "zc" : True, "ssc" : True, "wamp" : False, "var" : False, "vorder" : False, "logdetect" : False, "emghist" : False, "ar" : False, "ceps" : False}


    def command_string(self, value):
        """
        Commands are strings with the following format:

        [CMD_TYPE]:[CMD_VALUE]

        [CMD_TYPE] options are:
            Cmd - Indicates the cmd_value is a command word. Options are:
                mavOn
                mavOff
                curve_lenOn
                curve_lenOff
                zcOn
                zcOff
                sscOn
                sscOff
                wampOn
                wampOff
                varOn
                varOff
                vorderOn
                vorderOff
                logdetectOn
                logdetectOff
                emghistOn
                emghistOff
                arOn
                arOff
                cepsOn
                cepsOff
        """

        parsed = value.split(':')
        if not len(parsed) == 2:
            return
        else:
            cmd_type = parsed[0]
            cmd_data = parsed[1]

        if cmd_type == 'Cmd':
            if 'mavOn' in cmd_data:
                self.features_dict["mav"] = True
            elif 'mavOff' in cmd_data:
                self.features_dict["mav"] = False
            elif 'curve_lenOn' in cmd_data:
                self.features_dict["curve_len"] = True
            elif 'curve_lenOff' in cmd_data:
                self.features_dict["curve_len"] = False
            elif 'zcOn' in cmd_data:
                self.features_dict["zc"] = True
            elif 'zcOff' in cmd_data:
                self.features_dict["zc"] = False
            elif 'sscOn' in cmd_data:
                self.features_dict["ssc"] = True
            elif 'sscOff' in cmd_data:
                self.features_dict["ssc"] = False
            elif 'wampOn' in cmd_data:
                self.features_dict["wamp"] = True
            elif 'wampOff' in cmd_data:
                self.features_dict["wamp"] = False
            elif 'varOn' in cmd_data:
                self.features_dict["var"] = True
            elif 'varOff' in cmd_data:
                self.features_dict["var"] = False
            elif 'vorderOn' in cmd_data:
                self.features_dict["vorder"] = True
            elif 'vorderOff' in cmd_data:
                self.features_dict["vorder"] = False
            elif 'logdetectOn' in cmd_data:
                self.features_dict["logdetect"] = True
            elif 'logdetectOff' in cmd_data:
                self.features_dict["logdetect"] = False
            elif 'emghistOn' in cmd_data:
                self.features_dict["emghist"] = True
            elif 'emghistOff' in cmd_data:
                self.features_dict["emghist"] = False
            elif 'arOn' in cmd_data:
                self.features_dict["ar"] = True
            elif 'arOff' in cmd_data:
                self.features_dict["ar"] = False
            elif 'cepsOn' in cmd_data:
                self.features_dict["ceps"] = True
            elif 'cepsOff' in cmd_data:
                self.features_dict["ceps"] = False

            self.create_instance_list()

    def create_instance_list(self):

        self.vie.FeatureExtract.clear_features()

        if self.features_dict["mav"] == True:
            mav = pr.features.Mav()
            self.vie.FeatureExtract.attachFeature(mav)

        if self.features_dict["curve_len"] == True:
            curve_len = pr.features.Curve_len()
            self.vie.FeatureExtract.attachFeature(curve_len)

        if self.features_dict["zc"] == True:
            zc = pr.features.Zc()
            self.vie.FeatureExtract.attachFeature(zc)

        if self.features_dict["ssc"] == True:
            ssc = pr.features.Ssc()
            self.vie.FeatureExtract.attachFeature(ssc)

        if self.features_dict["wamp"] == True:
            wamp = pr.features.Wamp()
            self.vie.FeatureExtract.attachFeature(wamp)

        if self.features_dict["var"] == True:
            var = pr.features.Var()
            self.vie.FeatureExtract.attachFeature(var)

        if self.features_dict["vorder"] == True:
            vorder = pr.features.Vorder()
            self.vie.FeatureExtract.attachFeature(vorder)

        if self.features_dict["logdetect"] == True:
            logdetect = pr.features.Logdetect()
            self.vie.FeatureExtract.attachFeature(logdetect)

        if self.features_dict["emghist"] == True:
            emghist = pr.features.EMGhist()
            self.vie.FeatureExtract.attachFeature(emghist)

        if self.features_dict["ar"] == True:
            ar = pr.features.AR()
            self.vie.FeatureExtract.attachFeature(ar)

        if self.features_dict["ceps"] == True:
            ceps = pr.features.Ceps()
            self.vie.FeatureExtract.attachFeature(ceps)



