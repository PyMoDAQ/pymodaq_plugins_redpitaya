"""Behaviour of the Red Pitaya actuators against a fake pymeasure controller (no hardware needed)."""
import pytest

pytest.importorskip('pymodaq.utils.plugin_testing')

from pymodaq.utils.plugin_testing import make_actuator, move_abs_and_wait

try:
    from pymodaq_plugins_redpitaya.daq_move_plugins import (daq_move_RedpitayaAnalogSlow as slow_module,
                                                            daq_move_RedpitayaSCPI as scpi_module)
except ImportError:  # the pymeasure release does not yet contain the Red Pitaya driver (needs master)
    pytest.skip('These tests need a pymeasure version with the Red Pitaya driver (not yet released)',
                allow_module_level=True)


class FakeSlowChannel:
    def __init__(self, readable=True):
        self._voltage = 0.
        self.readable = readable
        self.was_reset = False

    @property
    def voltage(self):
        if not self.readable:
            raise LookupError("Instrument.setting properties can not be read.")
        return self._voltage

    @voltage.setter
    def voltage(self, value):
        self._voltage = value

    def reset(self):
        self.was_reset = True


class FakeFastChannel:
    def __init__(self):
        self.amplitude_values = [0, 1]
        self.amplitude = 0.
        self.frequency = 1.
        self.shape = 'SINE'
        self.enable = False
        self.runs = 0

    def run(self):
        self.runs += 1


class FakeRedPitaya:
    def __init__(self, *args, **kwargs):
        self.readable = True
        self.analog_out_slow = {i: FakeSlowChannel(self.readable) for i in range(4)}
        self.analog_out = {1: FakeFastChannel(), 2: FakeFastChannel()}


@pytest.fixture(params=[True, False], ids=['readback', 'write_only'])
def fake_pitaya(request, monkeypatch):
    def factory(*args, **kwargs):
        pitaya = FakeRedPitaya()
        for chan in pitaya.analog_out_slow.values():
            chan.readable = request.param
        return pitaya
    monkeypatch.setattr(slow_module, 'RedPitayaScpi', factory)
    monkeypatch.setattr(scpi_module, 'RedPitayaScpi', factory)


def test_slow_output_moves_and_reports_value(fake_pitaya):
    plugin = make_actuator(slow_module.DAQ_Move_RedpitayaAnalogSlow)
    pos = move_abs_and_wait(plugin, 0.9)
    assert pos.value('V') == pytest.approx(0.9)
    assert plugin.aout_slow._voltage == pytest.approx(0.9)
    plugin.close()
    assert plugin.aout_slow.was_reset


@pytest.mark.parametrize('generation', [1, 2])
def test_fast_output_amplitude_range_follows_board_generation(fake_pitaya, generation):
    plugin = make_actuator(scpi_module.DAQ_Move_RedpitayaSCPI, gen=generation)
    assert plugin.aout.amplitude_values == [0, generation]
