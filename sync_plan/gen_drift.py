import opsync_ as opsync
import numpy as np
import json
import matplotlib.pyplot as plt

tor_num = 192
tor_num = 1024
upper_link = 16
sigmas = [2,5,10,15]
sigmas = [2,5,10,15]
slice_duration = 300

slice_duration = 1000

def ppm2drift(ppm):
    ppm = np.array(ppm)
    return ppm / (1000 / slice_duration)

def save_drift(drift, name : str):
    drift = drift[0:3 * tor_num]
    drift = ppm2drift(drift)
    #np.savetxt("testbed/"+name+".txt", drift, fmt="%f")
    np.savetxt("testbed/"+name+".txt", drift, fmt="%d")

def draw_drift_pdf_hist(drift, drift_id):
    plt.hist(drift, bins = np.arange(-70,71,1), density=True)
    #plt.savefig("testbed/drifts.pdf")

    plt.tick_params(axis='both', which='major', labelsize=30)
    plt.xticks(range(-70,71,20))
    plt.yticks(np.arange(0, 0.21, 0.05), size = 20)
    #plt.yticks([])
    plt.xlim(-40, 40)
    plt.ylim(0,0.21)
    plt.xlabel("Clock drift (us/sec)", fontsize = 30)
    #plt.ylabel("Sampling Points", fontsize = 30)
    plt.ylabel("Probability Density", fontsize = 30)
    plt.subplots_adjust(bottom=0.21, left = 0.22, hspace = 0.0)
    plt.subplots_adjust(bottom=0.21, left = 0.19, hspace = 0.0)
    #plt.legend(fontsize = 16)
    plt.grid()
    #plt.show()
    plt.savefig(f"testbed/drift{drift_id}.pdf")
    plt.clf()

def draw_drift_pdf(drift, id):
    cnt, b_cnt = np.histogram(drift, bins=100)
    pdf = cnt/sum(cnt)
    cdf = np.cumsum(pdf)
    l, = plt.plot(b_cnt[1:], pdf, label = f"Distribution {id}", linewidth = 2)
    #plt.show()

def draw_drift_cdf(drift):
    cnt, b_cnt = np.histogram(drift, bins=100)
    pdf = cnt/sum(cnt)
    cdf = np.cumsum(pdf)
    l, = plt.plot(b_cnt[1:], cdf)
    #plt.show()


for id, sigma in enumerate(sigmas):
    estimated_drift, sim_drift = opsync.init_drift(100*tor_num, sigma, 0)
    #estimated_drift = ppm2drift(np.array(estimated_drift))
    #draw_drift_pdf(estimated_drift, id)
    #draw_drift_pdf_hist(estimated_drift, id)
    #draw_drift_cdf(estimated_drift)
    save_drift(estimated_drift, f"drift_{id}_1ms")

plt.tick_params(axis='both', which='major', labelsize=20)
plt.xticks(range(-70,71,20))
plt.xlim(-60, 60)
plt.xlabel("Clock drift (us/sec)", fontsize = 20)
plt.ylabel("Probability Density", fontsize = 20)
plt.subplots_adjust(bottom=0.16, left = 0.2, hspace = 0.3)
#plt.legend(fontsize = 16)
plt.grid()
#plt.show()

#plt.savefig("testbed/drifts.pdf")