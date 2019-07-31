""" Aggregate trajectory results into one results file and generate plots of trajectory results. """

from __future__ import print_function, division, absolute_import


import os
import datetime

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import scipy.stats
import scipy.ndimage


from wmpl.Utils.Pickling import loadPickle
from wmpl.Utils.PlotCelestial import CelestialPlot
from wmpl.Utils.SolarLongitude import jd2SolLonSteyaert


def writeOrbitSummaryFile(dir_path, traj_list):
    """ Given a list of trajectory files, generate CSV file with the orbit summary. """

    pass





def plotSCE(x_data, y_data, color_data, sol_range, plot_title, colorbar_title, dir_path, \
    file_name, density_plot=False):

    ### PLOT SUN-CENTERED GEOCENTRIC ECLIPTIC RADIANTS ###

    fig = plt.figure(figsize=(16, 8), facecolor='k')


    # Init the allsky plot
    celes_plot = CelestialPlot(x_data, y_data, projection='sinu', lon_0=-90, ax=fig.gca())

    # ### Mark the sources ###
    # sources_lg = np.radians([0, 270, 180])
    # sources_bg = np.radians([0, 0, 0])
    # sources_labels = ["Helion", "Apex", "Antihelion"]
    # celes_plot.scatter(sources_lg, sources_bg, marker='x', s=15, c='0.75')

    # # Convert angular coordinates to image coordinates
    # x_list, y_list = celes_plot.m(np.degrees(sources_lg), np.degrees(sources_bg + np.radians(2.0)))
    # for x, y, lbl in zip(x_list, y_list, sources_labels):
    #     plt.text(x, y, lbl, color='w', ha='center', alpha=0.5)

    # ### ###

    fg_color = 'white'

    # Choose the colormap
    if density_plot:
        cmap_name = 'inferno'
        cmap_bottom_cut = 0.0
    else:
        cmap_name = 'viridis'
        cmap_bottom_cut = 0.2


    # Cut the dark portion of the colormap
    cmap = plt.get_cmap(cmap_name)
    colors = cmap(np.linspace(cmap_bottom_cut, 1.0, cmap.N))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list('cut_cmap', colors)


    ### Do a KDE density plot
    if density_plot:

        # Define extent and density
        lon_min = -180
        lon_max = 180
        lat_min = -90
        lat_max = 90
        delta_deg = 0.5

        lon_bins = np.linspace(lon_min, lon_max, int(360/delta_deg))
        lat_bins = np.linspace(lat_min, lat_max, int(180/delta_deg))

        # Rotate all coordinates by 90 deg to make them Sun-centered
        x_data = np.array(x_data)
        y_data = np.array(y_data)
        lon_corr = (np.degrees(x_data) + 90)%360

        # Do a sinus projection
        lon_corr_temp = np.zeros_like(lon_corr)
        lon_corr_temp[lon_corr > 180] = ((180 - lon_corr[lon_corr > 180] + 180)*np.cos(y_data[lon_corr > 180]))
        lon_corr_temp[lon_corr <= 180] = ((180 - lon_corr[lon_corr <= 180] - 180)*np.cos(y_data[lon_corr <= 180]))
        lon_corr = lon_corr_temp

        # Compute the histogram
        data, _, _ = np.histogram2d(lon_corr, 
            np.degrees(np.array(y_data)), bins=(lon_bins, lat_bins))

        # Apply Gaussian filter to it
        data = scipy.ndimage.filters.gaussian_filter(data, 1.0)*2*np.pi

        plt_handle = celes_plot.m.imshow(data.T, origin='lower', extent=[lon_min, lon_max, lat_min, lat_max], 
            interpolation='gaussian', norm=matplotlib.colors.PowerNorm(gamma=1./2.), cmap=cmap)


    else:
        
        ### Do a scatter plot

        # Compute the dot size which varies by the number of data points
        dot_size = 40*(1.0/np.sqrt(len(x_data)))

        # Plot the data
        plt_handle = celes_plot.scatter(x_data, y_data, color_data, s=dot_size, cmap=cmap)

        
    # Plot the colorbar
    cb = fig.colorbar(plt_handle)
    cb.set_label(colorbar_title, color=fg_color)
    cb.ax.yaxis.set_tick_params(color=fg_color)
    cb.outline.set_edgecolor(fg_color)
    plt.setp(plt.getp(cb.ax.axes, 'yticklabels'), color=fg_color)


    plt.title(plot_title, color=fg_color)

    # Plot solar longitude range and count
    sol_min, sol_max = sol_range
    # plt.annotate(u"$\lambda_{\u2609 min} =$" + u"{:>5.2f}\u00b0".format(sol_min) \
    #     + u"\n$\lambda_{\u2609 max} =$" + u"{:>5.2f}\u00b0".format(sol_max), \
    #     xy=(0, 1), xycoords='axes fraction', color='w', size=12, family='monospace')
    plt.annotate(u"Sol min = {:>6.2f}\u00b0".format(sol_min) \
        + u"\nSol max = {:>6.2f}\u00b0".format(sol_max)
        + "\nCount = {:d}".format(len(x_data)), \
        xy=(0, 1), xycoords='axes fraction', color='w', size=10, family='monospace')

    plt.tight_layout()

    plt.savefig(os.path.join(dir_path, file_name), dpi=100, facecolor=fig.get_facecolor(), \
        edgecolor='none')

    plt.close()

    ### ###



def generateTrajectoryPlots(dir_path, traj_list):
    """ Given a path with trajectory .pickle files, generate orbits plots. """



    ### Plot Sun-centered geocentric ecliptic plots ###
    lambda_list = []
    beta_list = []
    vg_list = []
    sol_list = []

    hypo_count = 0
    jd_min = np.inf
    jd_max = 0
    for traj in traj_list:

        # Reject all hyperbolic orbits
        if traj.orbit.e > 1:
            hypo_count += 1
            continue

        # Compute Sun-centered longitude
        lambda_list.append(traj.orbit.L_g - traj.orbit.la_sun)

        beta_list.append(traj.orbit.B_g)
        vg_list.append(traj.orbit.v_g/1000)
        sol_list.append(np.degrees(traj.orbit.la_sun))

        # Track first and last observation
        jd_min = min(jd_min, traj.jdt_ref)
        jd_max = max(jd_max, traj.jdt_ref)


    print("Hyperbolic percentage: {:.2f}%".format(100*hypo_count/len(traj_list)))

    # Compute the range of solar longitudes
    sol_min = np.degrees(jd2SolLonSteyaert(jd_min))
    sol_max = np.degrees(jd2SolLonSteyaert(jd_max))



    # Plot SCE vs Vg
    plotSCE(lambda_list, beta_list, vg_list, (sol_min, sol_max), 
        "Sun-centered geocentric ecliptic coordinates", "$V_g$ (km/s)", dir_path, "scecliptic_vg.png")


    # Plot SCE vs Sol
    plotSCE(lambda_list, beta_list, sol_list, (sol_min, sol_max), \
        "Sun-centered geocentric ecliptic coordinates", "Solar longitude (deg)", dir_path, \
        "scecliptic_sol.png")
    

    
    # Plot SCE orbit density
    plotSCE(lambda_list, beta_list, None, (sol_min, sol_max), 
        "Sun-centered geocentric ecliptic coordinates", "Count", dir_path, "scecliptic_density.png", \
        density_plot=True)




if __name__ == "__main__":

    import argparse

    ### COMMAND LINE ARGUMENTS

    # Init the command line arguments parser
    arg_parser = argparse.ArgumentParser(description="""Given a folder with trajectory .pickle files, generate an orbit summary CSV file and orbital graphs.""",
        formatter_class=argparse.RawTextHelpFormatter)

    arg_parser.add_argument('dir_path', type=str, help='Path to the data directory. Trajectory pickle files are found in all subdirectories.')

    # Parse the command line arguments
    cml_args = arg_parser.parse_args()

    ############################



    ### FILTERS ###

    # Minimum number of points on the trajectory for the station with the most points
    min_traj_points = 6

    # Minimum convergence angle (deg)
    min_qc = 5.0


    ### ###


    # Get a list of paths of all trajectory pickle files
    traj_list = []
    for entry in os.walk(cml_args.dir_path):

        dir_path, _, file_names = entry

        # Go through all files
        for file_name in file_names:

            # Check if the file is a pickel file
            if file_name.endswith("_trajectory.pickle"):

                # Load the pickle file
                traj = loadPickle(dir_path, file_name)


                ### MINIMUM POINTS
                ### Reject all trajectories with small number of used points ###
                points_count = [len(obs.time_data[obs.ignore_list == 0]) for obs in traj.observations \
                    if obs.ignore_station == False]

                if not points_count:
                    continue

                max_points = max(points_count)

                if max_points < min_traj_points:
                    print("Skipping {:.2f} due to the small number of points...".format(traj.jdt_ref))
                    continue

                ###


                ### CONVERGENCE ANGLE                
                ### Reject all trajectories with a too small convergence angle ###

                if np.degrees(traj.best_conv_inter.conv_angle) < min_qc:
                    print("Skipping {:.2f} due to the small convergence angle...".format(traj.jdt_ref))
                    continue

                ###


                traj_list.append(traj)




    # Generate the orbit summary file
    writeOrbitSummaryFile(cml_args.dir_path, traj_list)

    # Generate plots
    generateTrajectoryPlots(cml_args.dir_path, traj_list)




