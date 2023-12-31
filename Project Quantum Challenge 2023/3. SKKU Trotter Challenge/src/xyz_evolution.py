import numpy as np

from math import ceil
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from src.propagators import UXZGate, UXYZGate


class XYZEvolutionCircuit(QuantumCircuit):
    """
    A ``QuantumCircuit`` that implements time propagation under the action
    of a Heisenberg Hamiltonian.

    EXAMPLES::

        >>> from src.xyz_evolution import XYZEvolutionCircuit
        >>> XYZEvolutionCircuit(4, [1, 1, 1], trotter_num=2).draw()
             ┌───────┐         ┌───────┐         
        q_0: ┤0      ├─────────┤0      ├─────────
             │  Uxyz │┌───────┐│  Uxyz │┌───────┐
        q_1: ┤1      ├┤0      ├┤1      ├┤0      ├
             ├───────┤│  Uxyz │├───────┤│  Uxyz │
        q_2: ┤0      ├┤1      ├┤0      ├┤1      ├
             │  Uxyz │└───────┘│  Uxyz │└───────┘
        q_3: ┤1      ├─────────┤1      ├─────────
             └───────┘         └───────┘         
        >>> qc = XYZEvolutionCircuit(3, [1, 0, 1], magnetic_field=1, trotter_num=2, final_time=3)
        >>> qc.draw()
              ░ ┌─────────┐ ░ ┌──────┐         ░ ┌─────────┐ ░ ┌──────┐        
        q_0: ─░─┤ Rz(1.5) ├─░─┤0     ├─────────░─┤ Rz(1.5) ├─░─┤0     ├────────
              ░ ├─────────┤ ░ │  Uxz │┌──────┐ ░ ├─────────┤ ░ │  Uxz │┌──────┐
        q_1: ─░─┤ Rz(1.5) ├─░─┤1     ├┤0     ├─░─┤ Rz(1.5) ├─░─┤1     ├┤0     ├
              ░ ├─────────┤ ░ └──────┘│  Uxz │ ░ ├─────────┤ ░ └──────┘│  Uxz │
        q_2: ─░─┤ Rz(1.5) ├─░─────────┤1     ├─░─┤ Rz(1.5) ├─░─────────┤1     ├
              ░ └─────────┘ ░         └──────┘ ░ └─────────┘ ░         └──────┘
    """
    def __init__(
            self, 
            num_qubits,
            coupling_const=None,
            magnetic_field=0,
            final_time=0,
            trotter_num=0,
            bound=True,
        ):
        # Initialize QuantumCircuit
        super().__init__(num_qubits)

        # Record Hamiltonian parameters
        for param in ["coupling_const", "magnetic_field", "final_time", "trotter_num"]:
            setattr(self, param, eval(param))
        self.time_delta = final_time / trotter_num if trotter_num else 0

        # Impute the appropriate propagator
        self.propagator = "".join("XYZ"[j] for j in np.nonzero(coupling_const)[0])
        
        # Construct evolution circuit
        self._construct_evolution_qc(bound=coupling_const is not None)

    def uxz(self, gamma, delta, qubit1, qubit2):
        r"""
        Apply the parametrized :class:`.UXZGate` onto ``qubit1`` and ``qubit2``.
        
        EXAMPLES::

            >>> from src.xyz_evolution import XYZEvolutionCircuit
            >>> qc = XYZEvolutionCircuit(3)
            >>> _ = qc.uxz(1, 2, 0, 1)
            >>> _ = qc.uxz(1, 2, 1, 2)
            >>> qc.draw()
                 ┌──────┐        
            q_0: ┤0     ├────────
                 │  Uxz │┌──────┐
            q_1: ┤1     ├┤0     ├
                 └──────┘│  Uxz │
            q_2: ────────┤1     ├
                         └──────┘
        """
        time_prop = UXZGate(gamma, delta).to_instruction()
        return self.append(time_prop, [qubit1, qubit2])

    def uxyz(self, thetax, thetay, thetaz, qubit1, qubit2):
        r"""
        Apply the parametrized :class:`.UXYZGate` onto ``qubit1`` and ``qubit2``.

        EXAMPLES::

            >>> from src.xyz_evolution import XYZEvolutionCircuit
            >>> qc = XYZEvolutionCircuit(4)
            >>> _ = qc.uxyz(1, 2, 3, 1, 2)
            >>> qc.draw()

            q_0: ─────────
                 ┌───────┐
            q_1: ┤0      ├
                 │  Uxyz │
            q_2: ┤1      ├
                 └───────┘
            q_3: ─────────
        """
        time_prop = UXYZGate(thetax, thetay, thetaz).to_instruction()
        return self.append(time_prop, [qubit1, qubit2])

    def _construct_evolution_qc(self, propagator=None, num_layers=None, odd=False, bound=True):
        r"""
        Construct the time propagator corresponding to evolution under the $XYZ$
        Hamiltonian.
        """
        # Set the number of layers if None is specified
        if num_layers is None:
            num_layers = 2 * self.trotter_num

        # Determine block operator and number of parameters per block
        if propagator is None:
            propagator = self.propagator
        block = getattr(self, "u" + propagator.lower())
        num_block_params = len(propagator)

        # Get parameters or bindings
        num_blocks = ceil(num_layers * (self.num_qubits - 1) / 2)
        if bound:
            J = np.array([Ja for Ja in self.coupling_const if not np.isclose(Ja, 0)])
            params = np.tile(self.time_delta * J, (num_blocks, 1))
        else:
            params = [ParameterVector("θ" + str(k), num_block_params) for k in range(num_blocks)]

        # Lay down blocks one step at a time!

        #####################
        ### Fill this in! ###
        #####################
        for gate in range(num_layers):

            n = gate % 2

            if n == 0:
                for qubit in range(self.num_qubits):
                    self.rz(self.magnetic_field * self.time_delta, qubit)

            for qubit in range(n, self.num_qubits - 1, 2):

                block_params = params.pop(0) if not bound else params[n // 2]

                # Apply the block gate
                if num_block_params == 2:
                    self.uxz(block_params[0], block_params[1], qubit, qubit+1)
                elif num_block_params == 3:
                    self.uxyz(block_params[0], block_params[1], block_params[2], qubit, qubit+1)



