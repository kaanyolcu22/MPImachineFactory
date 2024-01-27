#Kaan Yolcu 2020400150 Grup 8
from mpi4py import MPI
import sys






def main():
    # get the arguments
    args=sys.argv
    # get the process number
    with open(args[1], 'r') as f:
            lines = f.readlines()
    num_machines = int(lines[0].strip())
    # initialize comminucator
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    
    # spawn 
    intercomm = comm.Spawn_multiple([sys.executable], args=[['machine.py',args[1],args[2]]], maxprocs=num_machines+1)

        
       



if __name__ == "__main__":
    main()
