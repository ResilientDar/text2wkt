# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterString,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterVectorLayer)
import processing

import os
import sys
import csv


class Text2WKTProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This is a Text2WKT algorithm that takes a csv file layer and
    creates a new csv result file.
    """
    # Constants used to refer to parameters and outputs. 

    INPUT = 'INPUT'
    COLUMN = 'COLUMN'
    DELIMITER = 'DELIMITER'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return Text2WKTProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm.
        """
        return 'Text2WKT'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Text2WKT')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return self.tr('Text2WKT')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to.
        """
        return 'text2wkt'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm.
        """
        return self.tr("Converts geotraces from ODK to Well-Known Text \n\n"
                        "Takes a CSV file containing line strings from an"
                        "OpenDataKit Geotrace, which consist of a series "
                        "of text coordinates, and returns a similar CSV file "
                        "with properly formatted Well-Known Text (WKT) "
                        "linestrings (and points).")

    def initAlgorithm(self, config=None):
        """
        Defining inputs and output of the algorithm, along
        with some other properties.
        """
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input csv file')
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
                self.COLUMN,
                self.tr('Location column'),
                parentLayerParameterName = self.INPUT,
                type = QgsProcessingParameterField.Any
            )
        )
        
        
        self.addParameter(
            QgsProcessingParameterString(
                self.DELIMITER,
                self.tr('Column delimiter used in the CSV file'),
                defaultValue=","
            )
        )
       
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Output file')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Processing logic takes place here.
        """

        # Retrieve the feature source, column and destination params.
        source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context
        )
        
        column = self.parameterAsString(
            parameters,
            self.COLUMN,
            context
        )
        
        delimiter = self.parameterAsString(
            parameters,
            self.DELIMITER,
            context
        )
        
        destination = self.parameterAsFileOutput(
            parameters,
            self.OUTPUT,
            context
        )

        # If sink was not created, throw an exception to indicate that the algorithm
        # encountered a fatal error. 

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. 
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        
        self.main(
            parameters[self.INPUT],
            None, 
            parameters[self.DELIMITER],
            column,
            feedback,
            parameters[self.OUTPUT]
        )

        # Return the results of the algorithm. 
        return {self.OUTPUT: parameters[self.OUTPUT]}
        
    def main(self, infile, column, delimiter,
         column_name, feedback, output = None):
        """Iterates through a CSV and writes a CSV with converted linestrings."""

        # Avoid choking the CSV library with a long linestring
        csv.field_size_limit(100000000)

        with open(infile) as line_data:
            reader = csv.reader(line_data, delimiter = delimiter)
            of = output if output else '{}_{}.csv'.format(infile, '_results')
            with open(of, 'w') as outfile:
                writer = csv.writer(outfile, delimiter = delimiter)
                header = next(reader)
                colindex = int(column) - 1 if column else header.index(column_name)
                writer.writerow(header)

                for row in reader:
                    node_string = ''.join(row[colindex])
                    outrow = row
                    outrow[colindex] = self.WKT_linestring_from_nodes(node_string)
                    writer.writerow(outrow)
            feedback.pushInfo('Created output file at: \n{}\n'.format(of))
            
    def WKT_linestring_from_nodes(self, node_string):
        """Takes a string of arbitrarily long strings separated by semicolons 
        where the first two items in the string are expected to be lat and long.
        Returns a string containing those coordinates as a Well-Known Text
        linestring (with long first and lat second, therefore x,y).
        """
        nodes = node_string.split(';')
        if nodes:
            WKT_type = "LINESTRING" if len(nodes) > 1 else "POINT"
            coord_pair_list = []
            for node in nodes:
                coords = node.strip().split()
                if(len(coords) >=2):   # can be >2 incl elev & precision values
                    # Reverse coords; Lon first, then Lat (as per WKT spec)
                    coord_pair = '{} {}'.format(coords[1], coords[0])
                    coord_pair_list.append(coord_pair)
            line_coord_string = ', '.join(coord_pair_list)
            linestring = '{}({})'.format(WKT_type, line_coord_string)
            return linestring
        else:
            return None
