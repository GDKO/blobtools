#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File        : BtPlot.py
Version     : 0.1
Author      : Dominik R. Laetsch, dominik.laetsch at gmail dot com 
Bugs        : ?
To do       : ?
"""
from __future__ import division
from numpy import array, arange, logspace, mean, std
import math
import lib.BtLog as BtLog
import lib.BtIO as BtIO
import matplotlib as mat
from matplotlib import cm
from matplotlib.ticker import NullFormatter
from matplotlib.lines import Line2D
from matplotlib.colors import rgb2hex
mat.use('agg')
import matplotlib.pyplot as plt
from itertools import izip

mat.rcParams.update({'font.size': 30})
mat.rcParams['xtick.major.pad'] = '8'
mat.rcParams['ytick.major.pad'] = '8'
mat.rcParams['lines.antialiased'] = True

FONTSIZE = 24
COLOURMAP = "Set2" # "Set1"
BLACK, GREY, BGGREY, WHITE = unicode('#262626'), unicode('#d3d3d3'), unicode('#F0F0F5'), unicode('#ffffff')
nullfmt = NullFormatter()

def n50(list_of_lengths):
    total_span = 0
    sorted_list_of_lengths=sorted(list_of_lengths, reverse=True)
    for contig_length in sorted_list_of_lengths:
        total_span += contig_length
    teoN50 = total_span/2.0
    running_sum = 0
    N50 = 0
    for contig_length in sorted_list_of_lengths:
        running_sum += contig_length
        if teoN50 <= running_sum:
            N50 = contig_length
            break
    return N50

def getSortedGroups(data_dict, sort_order):
    """ Returns list of sorted groups based on span or count. """
    sorted_groups = []
    if sort_order == 'span':
        sorted_groups = sorted(data_dict, key = lambda x : data_dict[x]['span_visible'] if data_dict[x]['span_visible'] > 0 else None, reverse=True)
    elif sort_order == 'count':
        sorted_groups = sorted(data_dict, key = lambda x : data_dict[x]['count_visible'] if data_dict[x]['count_visible'] > 0 else None, reverse=True)
    else:
        pass
    return sorted_groups

def generateColourDict(groups):
    cmap = cm.get_cmap(name=COLOURMAP)
    colour_groups = [group for group in groups if not group == 'no-hit' or not group == 'None']
    n_tax = len(colour_groups)
    breaks = [0.0 + x*(1.0-0.0)/n_tax for x in range(n_tax)]
    colour_d = {group: rgb2hex(cmap(b)) for b, group in izip(breaks, colour_groups)}
    if 'no-hit' in groups:
        colour_d['no-hit'] = GREY
    if 'None' in groups: 
        colour_d['None'] = GREY
    return colour_d

def set_canvas():
    left, width = 0.1, 0.60
    bottom, height = 0.1, 0.60
    bottom_h = left_h = left+width+0.02
    rect_scatter = [left, bottom, width, height]
    rect_histx = [left, bottom_h, width, 0.2]
    rect_histy = [left_h, bottom, 0.2, height]
    rect_legend = [left_h, bottom_h, 0.2, 0.2]
    return rect_scatter, rect_histx, rect_histy, rect_legend

def set_format_scatterplot(axScatter, max_cov):
    axScatter.set_xlabel("GC proportion", fontsize=35)
    axScatter.set_ylabel("Coverage", fontsize=35)
    axScatter.grid(True, which="major", lw=2., color=WHITE, linestyle='-') 
    axScatter.set_axisbelow(True)
    axScatter.set_xlim( (0, 1) )
    axScatter.set_ylim( (0.01, max_cov+1000) ) # This sets the max-Coverage so that all libraries + sum are at the same scale
    axScatter.xaxis.labelpad = 20
    axScatter.xaxis.labelpad = 20
    return axScatter

def set_format_hist_x(axHistx, axScatter):
    axHistx.set_xlim( axScatter.get_xlim() )
    axHistx.grid(True, which="major", lw=2., color= WHITE, linestyle='-')
    axHistx.xaxis.set_major_formatter(nullfmt) # no labels since redundant
    axHistx.set_axisbelow(True)
    axHistx.yaxis.labelpad = 20
    return axHistx

def set_format_hist_y(axHisty, axScatter):
    axHisty.set_yscale('log')
    axHisty.yaxis.set_major_formatter(nullfmt) # no labels since redundant
    axHisty.set_ylim( axScatter.get_ylim() )
    axHisty.grid(True, which="major", lw=2., color= WHITE, linestyle='-')
    axHisty.set_axisbelow(True)
    axHisty.xaxis.labelpad = 20
    return axHisty

def plot_ref_legend(axScatter):
    s = 15
    # markersize in scatter is in "points^2", markersize in Line2D is in "points" ... that's why we need math.sqrt()
    ref_1 = (Line2D([0], [0], linewidth = 0.5, linestyle="none", marker="o", alpha=1, markersize=math.sqrt(1000/15),  markerfacecolor=GREY))
    ref_2 = (Line2D([0], [0], linewidth = 0.5, linestyle="none", marker="o", alpha=1, markersize=math.sqrt(5000/15), markerfacecolor=GREY))
    ref_3 = (Line2D([0], [0], linewidth = 0.5, linestyle="none", marker="o", alpha=1, markersize=math.sqrt(10000/15), markerfacecolor=GREY))
    axScatter.legend([ref_1,ref_2,ref_3], ["1,000nt", "5,000nt", "10,000nt"], numpoints=1, loc = 4, fontsize=FONTSIZE)

def parse_labels(labels):
    label_d = {}
    name, groups = '', ''
    if (labels):
        try:
            for label in labels:
                name, groups = str(label).split("=")
                if "," in groups:
                    for group in groups.split(","):
                        label_d[group] = name
                else:
                    label_d[groups] = name
        except:
            BtLog.error('17', labels)
    return label_d

class PlotObj():
    def __init__(self, data_dict, cov_libs, cov_libs_total_reads):
        self.labels = {'all'}
        self.group_labels = {}
        self.cov_libs = cov_libs
        self.data_dict = data_dict
        self.cov_libs_total_reads = cov_libs_total_reads
        self.stats = {}
        self.exclude_groups = []
        self.colours = {}
        self.group_order = []
        self.plot_order = []
        self.min_cov = 0.01
        self.max_cov = 0.0
        self.out_f = ''
        self.title = ''
        self.max_group_plot = 0

    def get_stats_for_group(self, group):
        stats = { 'name' : group, 
                  'count_total' : "{:,}".format(self.stats[group]['count']), 
                  'count_visible_perc' : '{0:.1%}'.format(self.stats[group]['count_visible']/self.stats[group]['count']), 
                  'span_total' : "{:,}".format(self.stats[group]['span']), 
                  'span_visible_perc' : '{0:.1%}'.format(self.stats[group]['span_visible']/self.stats[group]['span']),
                  'colour' : str(self.colours[group] if group in self.colours else None),
                  'n50' : "{:,}".format(self.stats[group]['n50']),
                  'gc_mean' : "{0:.2}".format(self.stats[group]['gc_mean']),
                  'gc_std' : "{0:.2}".format(self.stats[group]['gc_std']),
                  'cov_mean' : {cov_lib : "{0:0.1f}".format(cov_mean) for cov_lib, cov_mean in self.stats[group]['cov_mean'].items()},
                  'cov_std' : {cov_lib : "{0:0.1f}".format(cov_std) for cov_lib, cov_std in self.stats[group]['cov_std'].items()},
                  'reads_mapped' : {cov_lib : "{:,}".format(reads_mapped) for cov_lib, reads_mapped in self.stats[group]['reads_mapped'].items()},
                  'reads_mapped_perc' : {cov_lib : '{0:.1%}'.format(reads_mapped_perc) for cov_lib, reads_mapped_perc in self.stats[group]['reads_mapped_perc'].items()}
                }
        return stats

    def write_stats(self):
        stats = []
        stats.append(self.get_stats_for_group('all'))
        for group in self.plot_order: # group/label/other that has been plotted
            stats.append(self.get_stats_for_group(group))
            if not group in self.group_labels: # it is either a label or "other"
                label = group
                for g, labels in self.group_labels.items():
                    if label in labels:
                        stats.append(self.get_stats_for_group(g))
        
        out_f = "%s.stats.txt" % self.out_f
        with open(out_f, 'w') as fh:
            for cov_lib in sorted(self.cov_libs):
                fh.write("# %s - %s\n" % (self.out_f, cov_lib))
                fh.write("{:<10}\t{:>10}{:>10}\t{:>10}\t{:<10}{:<10}\t{:<10}\t{:<5}\t{:<5}\t{:<10}\t{:<10}\t{:<10}\t{:<10}\n".format('Group', 'colour', 'count', 'visible (%)', 'span', 'visible(%)', 'n50', 'GC', 'GC (std)', 'cov_mean', 'cov_std', 'read map', 'read map (%)'))        
                for stat in stats:
                    fh.write("{:<10}\t{:>10}{:>10}\t{:>10}\t{:<10}{:<10}\t{:<10}\t{:<5}\t{:<5}\t{:<10}\t{:<10}\t{:<10}\t{:<10}\n".format(\
                            stat['name'], stat['colour'], stat['count_total'], stat['count_visible_perc'], stat['span_total'], \
                            stat['span_visible_perc'], stat['n50'], stat['gc_mean'], stat['gc_std'], stat['cov_mean'][cov_lib], \
                            stat['cov_std'][cov_lib], stat['reads_mapped'][cov_lib], stat['reads_mapped_perc'][cov_lib]))
        #    for d in table_data:
        #        fh.write("{:>10}\t{:>10}\t{:>10}\t{:>10}\t{:<10}\t{:<10}\t{:<10}\n".format(d['count_total'], d['count_visible_perc'], d['span_total'], d['span_visible_perc'], d['name'], d['label'], d['colour'] ))

    def compute_stats(self):
        stats = {}
        
        for label in self.labels:
            stats[label] = {
                            'gc' : [], 
                            'length': [], 
                            'covs' : {cov_lib : [] for cov_lib in self.cov_libs},
                            'cov_mean' : {cov_lib : 0.0 for cov_lib in self.cov_libs},
                            'cov_std' : {cov_lib : 0.0 for cov_lib in self.cov_libs},
                            'reads_mapped' : {cov_lib : 0 for cov_lib in self.cov_libs},
                            'reads_mapped_perc' : {cov_lib: 0.0 for cov_lib in self.cov_libs},
                            'n50' : 0,
                            'gc_mean' : 0.0,
                            'gc_std' : 0.0,
                            'groups' : set(),
                            'count' : 0,
                            'span' : 0,
                            'count_visible' : 0,
                            'span_visible' : 0
                            }

        # gather data
        for group, labels in self.group_labels.items():
            for label in labels:    
                stats[label]['groups'].add(group)
                stats[label]['gc'] = stats[label]['gc'] + self.data_dict[group]['gc']
                stats[label]['length'] = stats[label]['length'] + self.data_dict[group]['length']
                stats[label]['count_visible'] += self.data_dict[group]['count_visible']
                stats[label]['span_visible'] += self.data_dict[group]['span_visible']
                for cov_lib in self.cov_libs:
                    stats[label]['covs'][cov_lib] = stats[label]['covs'][cov_lib] + self.data_dict[group]['covs'][cov_lib]
                    stats[label]['reads_mapped'][cov_lib] += self.data_dict[group]['reads_mapped'][cov_lib]
        #for label in stats:
        #    print label, stats[label]
        for label in stats:
            stats[label]['gc_mean'] = mean(array(stats[label]['gc']))
            stats[label]['gc_std'] = std(array(stats[label]['gc']))
            stats[label]['n50'] = n50(stats[label]['length'])
            stats[label]['count'] = len(stats[label]['length'])
            stats[label]['span'] = sum(stats[label]['length'])
            for cov_lib in self.cov_libs:
                stats[label]['cov_mean'][cov_lib] = mean(array(stats[label]['covs'][cov_lib]))
                stats[label]['cov_std'][cov_lib] = std(array(stats[label]['covs'][cov_lib]))
                stats[label]['reads_mapped_perc'][cov_lib] = stats[label]['reads_mapped'][cov_lib]/self.cov_libs_total_reads[cov_lib]
        self.stats = stats
        #for label in stats:
        #    print label, stats[label]
        
    
    def relabel_and_colour(self, colour_f, user_labels):
        if (colour_f):
            colour_dict = BtIO.parseColourDict(colour_f)
        else:
            groups = self.group_order[0:self.max_group_plot]
            colour_groups = [group if not (group in user_labels) else user_labels[group] for group in groups]
            colour_dict = generateColourDict(colour_groups)
        for idx, group in enumerate(self.group_order):
            if (self.exclude_groups):
                if group in self.exclude_groups:
                    self.group_labels[group].add('other')
                    self.colours[group] = WHITE     
            elif group in user_labels:
                label = user_labels[group]
                self.group_labels[group].add(label)
                self.group_labels[group].add(group)
                self.colours[label] = colour_dict[label]
                if label not in self.plot_order:
                    self.plot_order.append(label)
            elif group in colour_dict:    
                self.group_labels[group].add(group)
                self.colours[group] = colour_dict[group] 
                self.plot_order.append(group)
            elif idx > self.max_group_plot:
                self.group_labels[group].add('other')
                self.group_labels[group].add(group)
                self.colours['other'] = WHITE
                self.labels.add('other')
            else:
                self.group_labels[group].add('other')
                self.group_labels[group].add(group)
                self.colours['other'] = WHITE
                self.labels.add('other')
            self.group_labels[group].add('all')
        if 'other' in self.labels:
            self.plot_order.append('other')

    #def writePlotSummaryTable(self):
    #    table_data = []
    #    for group in self.group_order:
    #        table_data.append({
    #                    'name' : group, 
    #                    'label' : self.labels[group],
    #                    'count_total' : "{:,}".format(self.count[group]), 
    #                    'count_visible_perc' : '{0:.1%}'.format(self.count_visible[group]/self.count[group]), 
    #                    'span_total' : "{:,}".format(self.span[group]), 
    #                    'span_visible_perc' : '{0:.1%}'.format(self.span_visible[group]/self.span[group]),
    #                    'colour' : self.colours[group]
    #                    })
    #    
    #    out_f = "%s.plot.txt" % self.out_f
    #    with open(out_f,'w') as fh:
    #        fh.write("{:>10}\t{:>10}\t{:>10}\t{:>10}\t{:<10}\t{:<10}\t{:<10}\n".format("COUNT", "visible (%)", "SPAN (nt)", "visible (%)", "group", "label", "colour"))
    #        for d in table_data:
    #            fh.write("{:>10}\t{:>10}\t{:>10}\t{:>10}\t{:<10}\t{:<10}\t{:<10}\n".format(d['count_total'], d['count_visible_perc'], d['span_total'], d['span_visible_perc'], d['name'], d['label'], d['colour'] ))

    def plotReadCov(self):
        for cov_lib in self.read_cov:
            if not self.read_cov[cov_lib]['total'] == 0:
                perc_mapped = []
                labels = ['all']
                for group in self.plot_order:
                    labels.append(group)
                perc_mapped = [stats[label]['reads_mapped'][cov_lib] for label in labels]
                reads_total = self.read_cov[cov_lib]['total']
                reads_mapped_total = self.read_cov[cov_lib]['mapped']
                reads_unmapped = reads_total - reads_mapped_total
                labels.append('unmapped')
                perc_mapped.append(reads_unmapped)
                print labels
                print perc_mapped
                # generate counts of reads mapped by group ...
                
    def plotBlobs(self, cov_lib, info_flag):
        rect_scatter, rect_histx, rect_histy, rect_legend = set_canvas()
        # Setting up plots and axes
        plt.figure(1, figsize=(35,35), dpi=400)
        axScatter = plt.axes(rect_scatter, axisbg=BGGREY, yscale = 'log')
        axScatter = set_format_scatterplot(axScatter, self.max_cov)
        axHistx = plt.axes(rect_histx, axisbg=BGGREY)
        axHistx = set_format_hist_x(axHistx, axScatter)
        axHisty = plt.axes(rect_histy, axisbg=BGGREY)
        axHisty = set_format_hist_y(axHisty, axScatter)
        if self.hist_type == "span":
            axHistx.set_ylabel("Span (kb)")
            axHisty.set_xlabel("Span (kb)", rotation='horizontal')
        else:
            axHistx.set_ylabel("Count")
            axHisty.set_xlabel("Count", rotation='horizontal')    
        axScatter.yaxis.get_major_ticks()[0].label1.set_visible(False)
        axScatter.yaxis.get_major_ticks()[1].label1.set_visible(False)
        for xtick in axHisty.get_xticklabels(): # rotate text for ticks in cov histogram 
            xtick.set_rotation(270)
        axLegend = plt.axes(rect_legend, axisbg=WHITE)
        axLegend.xaxis.set_major_locator(plt.NullLocator())
        axLegend.xaxis.set_major_formatter(nullfmt)
        axLegend.yaxis.set_major_locator(plt.NullLocator())
        axLegend.yaxis.set_major_formatter(nullfmt)
        # Setting title
        if (self.title):
            plt.suptitle(self.title, fontsize=35, verticalalignment='top')
        # Setting bins for histograms
        top_bins = arange(0, 1, 0.01)
        right_bins = logspace(-2, (int(math.log(self.max_cov)) + 1), 200, base=10.0)
        # empty handles for big legend
        legend_handles = []
        legend_labels = []
        # counter necessary for multiplot so that PNGs are in order when sorted by name
        i = 0
        for group in self.plot_order:
            i += 1
            group_length_array = array(self.stats[group]['length'])
            group_gc_array = array(self.stats[group]['gc'])
            group_cov_array = array(self.stats[group]['covs'][cov_lib])
            # calculate values for legend
            group_span_in_mb = round(self.stats[group]['span_visible']/1000000, 2)
            group_number_of_seqs = self.stats[group]['count_visible']
            group_n50 = self.stats[group]['n50']
            blob_size_array = []
            s, lw, alpha, colour = 15, 0.5, 1, self.colours[group]
            if (self.ignore_contig_length):
                if not group == "no-hit":
                    s = 65
                blob_size_array = [s for length in group_length_array]
            else:
                blob_size_array = [length/s for length in group_length_array]
            if group == "no-hit":
                alpha = 0.5
            weights_array = group_length_array/1000
            # generate label for legend
            fmt_seqs = "{:,}".format(group_number_of_seqs)
            fmt_span = "{:,}".format(group_span_in_mb)
            fmt_n50 = "{:,}".format(group_n50)
            label = "%s (%s;%sMB;%snt)" % (group, fmt_seqs, fmt_span, fmt_n50)
            if (info_flag):
                print BtLog.info_d['0'] % (group, fmt_seqs, fmt_span, fmt_n50)
            legend_handles.append(Line2D([0], [0], linewidth = 0.5, linestyle="none", marker="o", alpha=1, markersize=24, markerfacecolor=colour))
            legend_labels.append(label)
            if (self.hist_type == "span"):
                axHistx.hist(group_gc_array, weights=weights_array, color = colour, bins = top_bins, histtype='step', lw = 3)
                axHisty.hist(group_cov_array, weights=weights_array, color = colour, bins = right_bins, histtype='step', orientation='horizontal', lw = 3)
            else:           
                axHistx.hist(group_gc_array, color = colour, bins = top_bins, histtype='step', lw = 3)
                axHisty.hist(group_cov_array , color = colour, bins = right_bins, histtype='step', orientation='horizontal', lw = 3)
            axScatter.scatter(group_gc_array, group_cov_array, color = colour, s = blob_size_array, lw = lw, alpha=alpha, edgecolor=BLACK, label=label)
            axLegend.axis('off')
            if (self.multiplot): 
                axLegend.legend(legend_handles, legend_labels, loc=6, numpoints=1, fontsize=FONTSIZE, frameon=True)
                plot_ref_legend(axScatter)
                m_out_f = "%s.%s.%s.%s" % (self.out_f, i, group, self.format)
                print BtLog.status_d['8'] % m_out_f
                plt.savefig(m_out_f, format=self.format)
        if not (self.ignore_contig_length):
            plot_ref_legend(axScatter)
        axLegend.legend(legend_handles, legend_labels, numpoints=1, fontsize=FONTSIZE, frameon=True, loc=6 )
        self.out_f = "%s.%s" % (self.out_f, self.format)
        print BtLog.status_d['8'] % self.out_f
        plt.savefig(self.out_f, format=self.format) 
        plt.close()  
        
        

    

if __name__ == "__main__": 
    pass