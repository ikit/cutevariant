# Standard imports
import os

import sqlite3

import PySide6

import plotly.express as px

# Qt imports
from PySide6.QtWidgets import (
    QVBoxLayout,
    QFormLayout,
    QTableView,
    QComboBox,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, QModelIndex

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.plugin import PluginDialog
from cutevariant.core import sql

import typing
from functools import cmp_to_key, partial
import time
import copy
import re

# Qt imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


# Custom imports
from cutevariant.core import sql
from cutevariant.gui import plugin, FIcon, style
from cutevariant.gui.widgets import (
    ChoiceWidget,
    create_widget_action
)

from cutevariant.gui.widgets.choice_widget import ChoiceWidget
from cutevariant import LOGGER

from cutevariant.gui import FormatterDelegate
from cutevariant.gui.formatters.cutestyle import CutestyleFormatter


from PySide6.QtWidgets import *
import sys
from functools import partial
from PySide6.QtGui import QIcon

import pandas as pd
import numpy as np
from pandas import *
import seaborn as sns
import matplotlib.pyplot as plt
import dash_bio

class StatAnalysisDialog(PluginDialog):
    ENABLE = True

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setModal(False)

        self.conn = conn
        self.dico_tagbrut_tagsplit = {}
        self.dict_matrix_all_mutation={}
        self.ki_2_group_gene={}
        self.TAG_SEPARATOR = "&"
        self.gt=None
        self.hlayout= QHBoxLayout()
        self.df=None
        self.brut_matrix=[]
        self.all_gnomen=[]
        self.matrix=[]
        self.matrix_group1=[]
        self.matrix_group2=[]
        self.row_matrix_gnomen=[]
        self.row_matrix_group1_gnomen=[]
        self.row_matrix_group2_gnomen=[]
        self.name_matrix=[]
        self.name_matrix_group1=[]
        self.name_matrix_group2=[]
        self.sample_id = []
        self.sample_id_group1 = []
        self.sample_id_group2 = []
        self.group_name_select=[]
        self.data_frame=[]#a enlever
        self.test=QLineEdit()
        self.data_dict_df=None

        self.all_tag_split=ChoiceWidget()

        self.hlayout.addWidget(self.all_tag_split)
        self.hlayout.addWidget(self.test)

        self.setLayout(self.hlayout)
        self.setWindowTitle("stat")

        self._load_tagsplit()
        self.all_tag_split.accepted.connect(self.get_data_between_tag_sample_as_variant)

    def _load_tagsplit(self):
        all_value=[]
        self.tag_brut = [i["tags"] for i in sql.get_samples(self.conn)]
        print(self.tag_brut)
        for x in self.tag_brut:
            if x == None or x == '' or x.isspace():
                # Samples in DB can have a NULL or empty tag String. Do not put those in the tag selector.
                pass
            else:
                self.valeur = x.split(self.TAG_SEPARATOR)
                if '' in self.valeur:
                    self.valeur.remove('')
                print(self.valeur)
                self.dico_tagbrut_tagsplit[x] = self.valeur
                all_value = all_value+self.valeur


        for i in self.keep_sorted_unique_values(all_value):
            self.all_tag_split.add_item(FIcon(0xF04FD),i)

    def keep_sorted_unique_values(self, check_list:list):
        """
        returns an ordered list keeping only unique values
        """
        check_list = list(set(check_list))
        check_list.sort()
        return check_list

    def get_data_between_tag_sample_as_variant(self):
        self.group_name_select = self.group_select()
        _data = [i for i in sql.get_samples(conn)]
        self.sample_id.clear()
        self.sample_id_group1.clear()
        self.sample_id_group2.clear()

        """Attention pour une matrix globale ça a tait enlevé"""
        for index, _item_group_name in enumerate(self.group_name_select):
            for _data_dico in _data:
            # print(index, "///",_item_group_name)
                if index == 0 and _item_group_name['name'] == _data_dico['tags']:
                    # print(_data_dico['tags']+"////"+_item_group_name['name'][0])
                    self.sample_id_group1.append(_data_dico["id"])
                    self.name_matrix_group1.append(_data_dico['name']+_data_dico['tags'])

                if index == 1 and _item_group_name['name'] == _data_dico['tags']:
                    self.sample_id_group2.append(_data_dico["id"])
                    self.name_matrix_group2.append(_data_dico['name']+_data_dico['tags'])

        self.data_dict_df_group1 = [i for i in sql.get_tag_sample_has_variant(conn, self.sample_id_group1, 'mutant')]
        self.data_dict_df_group2 = [i for i in sql.get_tag_sample_has_variant(conn, self.sample_id_group2, 'mutant')]
        # self.data_dict_df = [i for i in sql.get_tag_sample_has_variant(conn, self.sample_id, 'mutant')]

        self.load_gnomen_list(self.data_dict_df_group1)
        self.load_gnomen_list(self.data_dict_df_group1)
        # self.load_gnomen_list(self.data_dict_df_group1)

        self.fill_matrix_True_or_False_mutate(self.data_dict_df_group1,self.sample_id_group1,1)
        self.fill_matrix_True_or_False_mutate(self.data_dict_df_group2,self.sample_id_group2,2)
        self.create_data_frame('1')
        self.create_data_frame('2')

        # self.ki_2_()
        # df=self.create_data_frame()
        # self.draw_heatmap(df)

    def init_matrix(self, sample_id:list):
        print("dans init matrix")
        for i in self.all_gnomen:
            self.brut_matrix.append([0 for i in sample_id])
        print(self.brut_matrix)

    def fill_matrix_True_or_False_mutate(self, data:list, sample_id:list, number_matrix:int):
        print("dans la fonction")
        self.brut_matrix.clear()
        self.init_matrix(sample_id)
        for index,i in enumerate(sample_id):
            for index2,j in enumerate(self.all_gnomen):

                for item_dico_join in data:
                    if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i:
                        if  item_dico_join['gt'] >= 1:
                            self.brut_matrix[index2][index] =1

        """Parcour les lignes de la matrice brut et selon si c'est une matrice de comparaison du ki2 ou une globale ,
        soit on ajoute toute les lignes soit on ajoute seulement celle qui ont une valeur sup à 1 """
        for index2, j in enumerate(self.all_gnomen):
            if number_matrix == 0:
                if any(self.brut_matrix[index2]):
                    self.row_matrix_gnomen.append(j)
                    self.matrix.append(self.brut_matrix[index2])

            elif number_matrix == 1:
                self.row_matrix_group1_gnomen.append(j)
                self.matrix_group1.append(self.brut_matrix[index2])

            elif number_matrix == 2:
                self.row_matrix_group2_gnomen.append(j)
                self.matrix_group2.append(self.brut_matrix[index2])

            elif number_matrix != 1 and number_matrix != 2 and number_matrix != 0:
                print("Erreur du nombre de la matrix")

    # def fill_matrix_count_variants(self):
    #     self.init_matrix()
    #     """remplir matrice"""
    #     for index,i in enumerate(self.sample_id):
    #         for index2,j in enumerate(self.all_gnomen):
    #             for item_dico_join in self.data_dict_df:
    #                 if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i:
    #                     if  item_dico_join['gt'] >= 1:
    #                         self.brut_matrix[index2][index] +=1
    #                     # print(self.brut_matrix)
    #
    #     for index2,j in enumerate(self.all_gnomen):
    #         if any(self.brut_matrix[index2]):
    #             self.row_matrix_gnomen.append(j)
    #             self.matrix.append(self.brut_matrix[index2])

    # def fill_matrix_VAF_variants(self):
    #     ##On a pas fait le filtre sur les gt -1 ou 0 dans la requette SQL il faut donc gerer le gt-1 ou on a None en vaf ad et dp
    #     self.init_matrix()
    #     for index,i in enumerate(self.sample_id):
    #         for index2,j in enumerate(self.all_gnomen):
    #             for item_dico_join in self.data_dict_df:
    #                 var_id=str(item_dico_join['variant_id'])
    #                 if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i:
    #                     if item_dico_join['vaf'] == None:
    #                         if item_dico_join['ad'] != None and item_dico_join['dp'] != None :
    #                             self.brut_matrix[index2][index] = self.get_calcul_VAF(item_dico_join['ad'],item_dico_join['dp'])
    #                     elif item_dico_join['vaf'] != None:
    #                         self.brut_matrix[index2][index] = item_dico_join['vaf']
    #                     # print(str(item_dico_join['variant_id']))
    #
    #             self.row_matrix_gnomen.append(var_id+"//"+j)
    #             self.matrix.append(self.brut_matrix[index2])

    # def PlotSbHEatMap(self):

    # def get_calcul_VAF(self, ad:any,dp:int):
    #     if isinstance(ad,tuple):
    #         ad=ad[1]
    #
    #     return ad/dp

    def ki_2_(self):
        current_freq=[]
        sample_group_tag=[]

        for item_dico_join in self.data_dict_df:
            # print("DEbug 4")
            for _item_group_name in self.group_name_select:
                # print("DEbug 78")

                """gestion des noms de gene vis à vis du tag select"""
                sample_group_tag.clear()

                """gestion des samples qui sont unique à chaque tag"""
                if item_dico_join['tags'] == _item_group_name:
                    # print("DEbug 21")

                    gene_group=item_dico_join['gnomen']+"//"+item_dico_join['tags']
                    print(gene_group)

                    sample_group_tag.append()

                for index, j in enumerate(self.all_gnomen):
                    # print("DEbug 22")

                    # print(index,j )

                    current_freq=[0*len(sample_group_tag)]
                    for index2, i in enumerate(sample_group_tag):
                        print(current_freq)

                        if item_dico_join['gt'] >= 1:
                            # print("DEbug 8")

                            self.brut_matrix[index][index2] += 1

                        if index2 == len(sample_group_tag):#tetre probleme au niveau du dernier
                            print("DEbug 9")

                            self.ki_2_group_gene[gene_group]=current_freq
                            current_freq.clear()

    def _gt_join_sample_has_variant(self, i:str,j:str) :
        for item_dico_join in self.data_dict_df:
            if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i :
                self.gt=item_dico_join['gt']
        return self.gt

    def _item_sample_has_variant_join(self, gnomen:str):
        for item_dico_join in self.data_dict_df:
            if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i :
                return item_dico_join

    def load_gnomen_list(self,data:list):
        for item_dico_join in data:
            self.all_gnomen.append(item_dico_join['gnomen'])
        self.all_gnomen=self.keep_sorted_unique_values(self.all_gnomen)

        return self.all_gnomen

    def keep_sorted_unique_values(self, check_list:list):
        """
        returns an ordered list keeping only unique values
        """
        check_list = list(set(check_list))
        check_list.sort()
        return check_list

    def group_select(self):
        if self.all_tag_split.checked() == True:
            my_generator_tag = self.all_tag_split.selected_items()
            result_list_tag = list(my_generator_tag)
            return result_list_tag

    def create_data_frame(self, matrix_number:str):

        self.df = pd.DataFrame(self.get_matrixs(matrix_number),
                          index=self.get_row_matrix(matrix_number),
                          columns=self.get_name_matrix(matrix_number))
        self.df.to_csv("C:/Users/HAMEAUEL/Documents/Db cute/matrix"+matrix_number+".txt", sep="\t", encoding="utf-8", index=True)

        return self.df

    def draw_heatmap(self,df:DataFrame):
        g = sns.clustermap(df, row_cluster=True, col_cluster=True,cmap="mako_r")

        g.savefig('C:/Users/HAMEAUEL/Documents/Db cute/test_col4.svg', dpi=100)

    def get_data_frame(self):
        return self.df

    def get_row_matrix(self, row_matrix_number:str):
        if row_matrix_number == '0':
            return self.row_matrix_gnomen

        if row_matrix_number == '1':
            return self.row_matrix_group1_gnomen

        if row_matrix_number == '2':
            return self.row_matrix_group2_gnomen

    def get_matrixs(self, matrix_number:str):
        if matrix_number == '0':
            return self.matrix

        if matrix_number == '1':
            return self.matrix_group1

        if matrix_number == '2':
            return self.matrix_group2

        if matrix_number == 'all':
            return self.matrix, self.matrix_group1, self.matrix_group2

    def get_sample_id(self):
        return self.sample_id

    def get_name_matrix(self, name_matrix_group:str):
        if name_matrix_group == '0':
            return self.name_matrix

        if name_matrix_group == '1':
            return self.name_matrix_group1

        if name_matrix_group == '2':
            return self.name_matrix_group2

    def get_all_mutation(self):
        return self.dict_matrix_all_mutation

    def get_all_gnomen(self):
        """je vais prendre tout les samples id qui ont le groupe select by user"""
        # self.all_gnomen
        return self.all_gnomen

    def get_dict_join(self):
        return self.data_dict_df

    def get_result_ki_2 (self):
        return self.ki_2_group_gene



if __name__ == "__main__":

    if os.path.exists("C:/Users/HAMEAUEL/Documents/Db cute/test_col4.svg"):
        os.remove("C:/Users/HAMEAUEL/Documents/Db cute/test_col4.svg")

    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("C:/Users/HAMEAUEL/Documents/Db cute/Big_Ech.db")
    conn.row_factory = sqlite3.Row

    dialog = StatAnalysisDialog(conn)
    dialog.show()
    app.exec()
    print(dialog.get_matrixs("1"))
    print(dialog.get_matrixs("2"))
    # print(dialog.get_group_select())
    # from scipy.stats import chisquare
    # import numpy as np
    #
    # gene1_group1 = [16, 18, 16, 14, 12, 12]
    # gene1_group2 = [16, 16, 16, 16, 16, 8]
    # gene1_result = chisquare(gene1_group1, gene1_group2)
    # gene1_p_value = gene1_result[1]
    # print("gene1 p-value: " + str(gene1_p_value))






