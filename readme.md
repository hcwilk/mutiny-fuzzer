# Quickstart: Mutiny tutorial

Blog post here:
* http://blog.talosintelligence.com/2018/01/tutorial-mutiny-fuzzing-framework-and.html

Links to this YouTube video demo:
* https://www.youtube.com/watch?v=FZyR6MgJCUs

For more features geared towards fuzzing campaigns/feedback/harnesses:
* https://github.com/Cisco-Talos/mutiny-fuzzer/tree/experiment

# Mutiny Fuzzing Framework

The Mutiny Fuzzing Framework is a network fuzzer that operates by replaying
PCAPs through a mutational fuzzer.  The goal is to begin network fuzzing as
quickly as possible, at the expense of being thorough.

The general workflow for Mutiny is to take a sample of legitimate traffic, such
as a browser request, and feed it into a prep script to generate a .fuzzer file.
Then, Mutiny can be run with this .fuzzer file to generate traffic against a
target host, mutating whichever packets the user would like.

There are extensions that allow changing how Mutiny behaves, including changing
messages based on input/output, changing how Mutiny responds to network errors,
and monitoring the target in a separate thread.

Mutiny uses [Radamsa](https://github.com/aoh/radamsa) to perform mutations.

The [Decept Proxy](https://github.com/Cisco-Talos/Decept) is a multi-purpose
network proxy that can forward traffic from a plaintext or TLS TCP/UDP/domain
socket connection to a plaintext or TLS TCP/UDP/domain socket connection, among
other features.  It makes a good companion for Mutiny, as it can both generate
.fuzzer files directly, particularly helpful when fuzzing TLS connections, and
allow Mutiny to communicate with TLS hosts.

sample_apps give a basic idea of some things that can be done with the fuzzer,
with a few different applications/clients to test with.

Written by James Spadaro (jaspadar@cisco.com) and Lilith Wyatt
(liwyatt@cisco.com)

## Setup

Ensure python and scapy are installed.

Untar Radamsa and `make`  (You do not have to make install, unless you want it
in /usr/bin - it will use the local Radamsa) Update `mutiny.py` with path to
Radamsa if you changed it.

## Basic Usage

Save pcap into a folder.  Run `mutiny_prep.py` on `<XYZ>.pcap` (also optionally
pass the directory of a custom processor if any, more below).  Answer the
questions, end up with a `<XYZ>.fuzzer` file in same folder as pcap.

Run `mutiny.py <XYZ>.fuzzer <targetIP>` This will start fuzzing. Logs will be
saved in same folder, under directory
`<XYZ>_logs/<time_of_session>/<seed_number>`

## More Detailed Usage

### .fuzzer Files

The .fuzzer files are human-readable and commented.  They allow changing various
options on a per-fuzzer-file basis, including which message or message parts are
fuzzed.

### Message Formatting

Within a .fuzzer file is the message contents.  These are simply lines that
begin with either 'inbound' or 'outbound', signifying which direction the
message goes.  They are in Python string format, with '\xYY' being used for
non-printable characters.  These are autogenerated by 'mutiny_prep.py' and
Decept, but sometimes need to be manually modified.

### Message Formatting - Manual Editing

If a message has the 'fuzz' keyword after 'outbound', this indicates it is to be
fuzzed through Radamsa.  A given message can have line continuations, by simply
putting more message data in quotes on a new line.  In this case, this second
line will be merged with the first.

Alternatively, the 'sub' keyword can be used to indicate a subcomponent.  This
allows specifying a separate component of the message, in order to fuzz only
certain parts and for convenience within a Message Processor.

Here is an example arbitrary set of message data:
```
outbound 'say'
    ' hi'
sub fuzz ' and fuzz'
    ' this'
sub ' but not this\xde\xad\xbe\xef'
inbound 'this is the server's'
    ' expected response'
```

This will cause Mutiny to transmit `say hi and fuzz this but not
this(0xdeadbeef)`.  `0xdeadbeef` will be transmitted as 4 hex bytes.  `and fuzz
this` will be passed through Radamsa for fuzzing, but `say hi` and ` but not
this(0xdeadbeef)` will be left alone.

Mutiny will wait for a response from the server after transmitting the single
above message, due to the 'inbound' line.  The server's expected response is
`this is the server's expected response`.  Mutiny won't do a whole lot with this
data, aside from seeing if what the server actually sent matches this string.
If a crash occurs, Mutiny will log both the expected output from the server and
what the server actually replied with.

### Customization

mutiny_classes/ contains base classes for the Message Processor, Monitor, and
Exception Processor.  Any of these files can be copied into the same folder as
the .fuzzer (by default) or into a separate subfolder specified as the
'processor_dir' within the .fuzzer file.

These three classes allow for storing server responses and changing outgoing
messages, monitoring the target on a separate thread, and changing how Mutiny
handles exceptions.

### Customization - Message Processor

The Message Processor defines various callbacks that are called during a fuzzing
run.  Within these callbacks, any Python code can be run.  Anecdotally, these
are primarily used in three ways.  

The most common is when the server sends tokens that need to be added to future
outbound messages.  For example, if Mutiny's first message logs in, and the
server responds with a session ID, the `postReceiveProcess()` callback can be used
to store that session ID.  Then, in `preSendProcess()`, the outgoing data can be
fixed up with that session ID.  An example of this is in
`sample_apps/session_server`.

Another common use of a Message Processor is to limit or change a fuzzed
message.  For example, if the server always drops messages greater than 1000
bytes, it may not be worth sending any large messages.  preSendProcess() can be
used to shorten messages after fuzzing but before they are sent or to raise an
exception.

Raising an exception brings up the final way Message Processors are commonly
used.  Within a callback, any custom exceptions defined in
`mutiny_classes/mutiny_exceptions.py` can be raised.  There are several
exceptions, all commented, that will cause various behaviors from Mutiny.  These
generally involve either logging, retrying, or aborting the current run.

### Customization - Monitor

The Monitor has a `monitorTarget()` function that is run on a separate thread from
the main Mutiny fuzzer.  The purpose is to allow implementing a long-running
process that can monitor a host in some fashion.  This can be anything that can
be done in Python, such as communicating with a monitor daemon running on the
target, reading a long file, or even just pinging the host repeatedly, depending
on the requirements of the fuzzing session.

If the Monitor detects a crash, it can call `signalMain()` at any time.  This will
signal the main Mutiny thread that a crash has occurred, and it will log the
crash.  This function should generally operate in an infinite loop, as returning
will cause the thread to terminate, and it will not be restarted.

### Customization - Exception Processor

The Exception Processor determines what Mutiny should do with a given exception
during a fuzz session.  In the most general sense, the `processException()`
function will translate Python and OS-level exceptions into Mutiny error
handling actions as best as it can.

For example, if Mutiny gets 'Connection Refused', the default response is to
assume that the target server has died unrecoverably, so Mutiny will log the
previous run and halt.  This is true in most cases, but this behavior can be
changed to that of any of the exceptions in
`mutiny_classes/mutiny_exceptions.py` as needed, allowing tailoring of crash
detection and error correction.

### Testing
Testing is implemented using python's [unittest](https://docs.python.org/3/library/unittest.html) library. To run the full test suite, you can use the following command from the projects root directory

`python3 -m unittest tests/units/*test.py`
