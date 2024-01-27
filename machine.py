#Kaan Yolcu 2020400150 Grup 8


from mpi4py import MPI
import sys


# Define a class to manage the machines in the factory
class MachineControlRoom:
    def __init__(self, num_machines, num_cycles, wear_factors, threshold, machine_links, leaf_products):
        # Initialize the attributes of the MachineControlRoom
        self.num_machines = num_machines
        self.num_cycles = num_cycles
        self.wear_factors = wear_factors
        self.threshold = threshold
        self.machine_links = machine_links
        self.leaf_products = leaf_products
        self.maintenance_costs = [] 
        self.maintenance_logs = []
        self.leaf_machineIds = []
        self.machines = {}

    # Initialize the machines in the factory
    def initialize_machines(self, comm):
        # Iterate over machine links to create machine objects
        for link in self.machine_links:
            [child_id, parent_id, initial_operation] = link
            parent_id = int(parent_id)
            child_id = int(child_id)
            
            # Create a parent machine if it doesn't exist
            if parent_id not in self.machines:
                parent_machine = Machine(parent_id, None, self.wear_factors, self.threshold, None, [], self.num_cycles, self.leaf_products, self.leaf_machineIds)
                self.machines[parent_id] = parent_machine
                self.machines[parent_id].add_child(child_id)
            else:
                self.machines[parent_id].add_child(child_id)

            # Create a child machine
            self.machines[child_id] = Machine(child_id, initial_operation, self.wear_factors, self.threshold, parent_id, [], self.num_cycles, self.leaf_products, self.leaf_machineIds)

        # Set leaf machine IDs
        for machine_id, machine in self.machines.items():
            if not machine.childIds:
                self.leaf_machineIds.append(machine_id)

        # Sort leaf machine IDs
        self.leaf_machineIds.sort()
        i = 0

        # Assign leaf products to leaf machines
        for leaf_machineId in self.leaf_machineIds:
            self.machines[leaf_machineId].current_product = self.leaf_products[i]
            i += 1

        # Send machine information to each machine process
        for machine_id, machine in self.machines.items():
            machine_info = (
                machine.machine_id,
                machine.operation,
                machine.wear_factors,
                machine.threshold,
                machine.parentId,
                machine.childIds,
                self.num_cycles,
                self.leaf_products,
                self.leaf_machineIds
            )
            
            for item in machine_info:
                comm.send(item, dest=machine_id, tag=1)

    # Parse input file to get simulation parameters
    def parse_input_file(filename):
        with open(filename, 'r') as f:
            lines = f.readlines()

        num_machines = int(lines[0].strip())
        num_cycles = int(lines[1].strip())
        wear_factors = list(map(int, lines[2].strip().split()))
        threshold = int(lines[3].strip())
        machine_links = [line.strip().split() for line in lines[4:4 + num_machines - 1]]
        leaf_products = [line.strip() for line in lines[4 + num_machines - 1:]]

        return num_machines, num_cycles, wear_factors, threshold, machine_links, leaf_products

    # Recursive process to simulate machine operations
    def recursive_process(self, machine_id):
        machine = self.machines[machine_id]

        for child_id in machine.childIds:
            self.recursive_process(child_id)

        machine.process_and_pass_products(0, comm)

# Define a class for individual machines
class Machine:
    def __init__(self, machine_id, operation, wear_factors, threshold, parentId, childIds, num_cycles, leaf_products, leaf_machine_ids):
        # Initialize the attributes of the Machine
        self.machine_id = machine_id
        self.current_product = ""
        self.parentId = parentId
        self.childIds = childIds
        self.operation_cycle = 0
        self.operation = operation
        self.accumulated_wear = 0
        self.wear_factors = wear_factors
        self.threshold = threshold
        self.leaf_products = leaf_products
        self.num_cycles = num_cycles
        self.leaf_machine_ids = leaf_machine_ids
        self.operations = ["enhance", "reverse", "chop", "trim", "split"]

    # Perform a specific operation on a product
    def perform_operation(self, operation, product):
        if operation == "enhance":
            return product[0] + product + product[-1]
        elif operation == "reverse":
            return product[::-1]
        elif operation == "chop":
            return product[:-1] if len(product) > 1 else product
        elif operation == "trim":
            return product[1:-1] if len(product) > 2 else product
        elif operation == "split":
            mid = len(product) // 2
            return product[:mid] if len(product) % 2 == 0 else product[:mid + 1]

    # Set the operation based on machine's characteristics
    def set_operation(self):
        if self.machine_id == 1:
            self.operation = None

        if self.machine_id % 2 == 0:
            if self.operation == "enhance":
                self.operation = "split"
            elif self.operation == "split":
                self.operation = "chop"
            else:
                self.operation = "enhance"
        else:
            if self.operation == "reverse":
                self.operation = "trim"
            else:
                self.operation = "reverse"

    # Add a child machine to the current machine
    def add_child(self, childId):
        self.childIds.append(childId)

    # Accumulate wear based on the performed operation
    def accumulate_wear(self):
        if self.operation is not None:
            wear_factor = self.wear_factors[self.operations.index(self.operation)]
            self.accumulated_wear += wear_factor

    # Check if maintenance is required and send maintenance information
    def check_for_maintenance(self, cycle_number, comm):
        if self.accumulated_wear >= self.threshold:
            maintenance_cost = (self.accumulated_wear - self.threshold + 1) * self.wear_factors[
                self.operations.index(self.operation)
            ]
            self.accumulated_wear = 0
            maint = f"{self.machine_id}-{maintenance_cost}-{cycle_number + 1}"
            comm.send(maint, dest=0, tag=2)

    # Process and pass products between machines
    def process_and_pass_products(self, cycle_number, comm):
        if self.childIds:
            received_products = []
            for child_id in self.childIds:
                received_product = comm.recv(source=child_id, tag=1)
                received_products.append(received_product)

            concatenated_product = "".join(received_products)
            self.current_product = concatenated_product
        else:
            index = self.leaf_machine_ids.index(self.machine_id)
            lst = self.leaf_products
            self.current_product = lst[index]

        new_product = self.current_product
        if self.machine_id != 1:
            new_product = self.perform_operation(self.operation, self.current_product)

        self.accumulate_wear()
        self.check_for_maintenance(cycle_number, comm)
        self.set_operation()

        parent_id = self.parentId
        if parent_id is not None:
            comm.send(new_product, dest=parent_id, tag=1)
        else:
            comm.send(new_product, dest=0, tag=5)

# Main function to run the simulation
def main():
    args = sys.argv
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()

    i = 0

    if rank == 0:  # Main process
        # Parse command line arguments to get input file and output file
        num_machines, num_cycles, wear_factors, threshold, machine_links, leaf_products = MachineControlRoom.parse_input_file(args[1])

        # Create MachineControlRoom instance
        simulator = MachineControlRoom(num_machines, num_cycles, wear_factors, threshold, machine_links, leaf_products)
        
        # Initialize machines
        simulator.initialize_machines(comm)

        # Open the output file for writing
        f = open(args[2], 'w+')

        # Receive and write the final products
        for i in range(0, num_cycles):
            product = comm.recv(source=1, tag=5)
            f.write(product + "\n")

        # Receive and write maintenance logs
        for i in range(2, num_machines):
            while comm.iprobe(i, tag=2):
                cost_str = comm.recv(source=i, tag=2)
                f.write(cost_str + "\n")

    else:  # Machine processes
        # Receive machine information from the main process
        machine_id = comm.recv(source=0, tag=1)
        operation = comm.recv(source=0, tag=1)
        wear_factors = comm.recv(source=0, tag=1)
        threshold = comm.recv(source=0, tag=1)
        parent_id = comm.recv(source=0, tag=1)
        child_ids = comm.recv(source=0, tag=1)
        num_cycles = comm.recv(source=0, tag=1)
        leaf_products = comm.recv(source=0, tag=1)
        leaf_machine_ids = comm.recv(source=0, tag=1)

        # Create Machine instance
        machine = Machine(
            machine_id,
            operation,
            wear_factors,
            threshold,
            parent_id,
            child_ids,
            num_cycles,
            leaf_products,
            leaf_machine_ids
        )

        # Process and pass products for each cycle
        for i in range(0, num_cycles):
            machine.process_and_pass_products(i, comm)

# Run the main function if the script is executed
if __name__ == "__main__":
    main()
