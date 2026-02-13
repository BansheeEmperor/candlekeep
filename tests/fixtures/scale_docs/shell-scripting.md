---
title: Bash Shell Scripting Reference
description: A comprehensive technical guide to Bash shell scripting, covering variables, loops, conditionals, functions, error handling, signal trapping, and best practices.
keywords: 
  - bash
  - shell scripting
  - variables
  - loops
  - conditionals
  - functions
  - error handling
  - signal trapping
  - best practices
category: programming
tags:
  - bash
  - shell
  - scripting
  - linux
  - terminal
---

## Variables

### Variable Declaration
To declare a variable in Bash, simply assign a value to it using the `=` operator:

```bash
MY_VARIABLE=value
```

Variable names should be in all-uppercase by convention. Spaces around the `=` are optional.

### Variable Expansion
To access the value of a variable, prefix the name with a `$`:

```bash
echo $MY_VARIABLE
```

You can also use curly braces to delimit the variable name:

```bash
echo ${MY_VARIABLE}
```

This is especially useful when the variable is part of a larger string.

### Special Variables
Bash has a number of special variables that provide information about the current shell session:

- `$0`: The name of the current script
- `$1`, `$2`, etc.: Positional arguments passed to the script
- `$#`: The number of positional arguments
- `$@`: All positional arguments as a single string
- `$?`: The exit status of the most recently executed command
- `$$`: The process ID of the current shell
- `$RANDOM`: A random integer between 0 and 32767

### Variable Scope
Variables in Bash have function or global scope. To declare a variable as local to a function, use the `local` keyword:

```bash
my_function() {
  local MY_LOCAL_VAR=value
  # ...
}
```

Global variables can be accessed anywhere in the script.

### Environment Variables
Environment variables are global variables that are accessible to all processes. They are typically named in all-uppercase. Common environment variables include:

- `HOME`: The user's home directory
- `PATH`: The list of directories to search for executable files
- `SHELL`: The user's default shell
- `EDITOR`: The user's default text editor

To set an environment variable, use the `export` command:

```bash
export MY_ENV_VAR=value
```

### Parameter Expansion
Bash provides various parameter expansion techniques to manipulate variable values:

- `${variable:-default}`: Use default value if variable is unset or null
- `${variable:=default}`: Assign default value if variable is unset or null
- `${variable:?err_msg}`: Display error message if variable is unset or null
- `${variable:+alt_value}`: Use alternative value if variable is set
- `${variable#pattern}`: Remove shortest match of pattern from front of string
- `${variable##pattern}`: Remove longest match of pattern from front of string
- `${variable%pattern}`: Remove shortest match of pattern from back of string
- `${variable%%pattern}`: Remove longest match of pattern from back of string

## Loops

### for Loop
The `for` loop iterates over a list of items:

```bash
for i in item1 item2 item3; do
  echo "Processing $i"
done
```

You can also use a C-style `for` loop:

```bash
for ((i=0; i<5; i++)); do
  echo "Iteration $i"
done
```

### while Loop
The `while` loop executes as long as a condition is true:

```bash
count=0
while [ $count -lt 3 ]; do
  echo "Count is $count"
  ((count++))
done
```

### until Loop
The `until` loop executes as long as a condition is false:

```bash
count=0
until [ $count -eq 3 ]; do
  echo "Count is $count"
  ((count++))
done
```

### break and continue
You can use the `break` and `continue` statements to control loop execution:

```bash
for i in 1 2 3 4 5; do
  if [ $i -eq 3 ]; then
    continue  # Skip iteration 3
  elif [ $i -eq 4 ]; then
    break  # Exit the loop
  fi
  echo "Iteration $i"
done
```

## Conditionals

### if-elif-else
The `if-elif-else` statement allows you to execute different code paths based on conditions:

```bash
if [ condition1 ]; then
  # code if condition1 is true
elif [ condition2 ]; then
  # code if condition1 is false and condition2 is true
else
  # code if all conditions are false
fi
```

### case Statement
The `case` statement provides a more concise way to handle multiple conditions:

```bash
case "$variable" in
  "value1")
    # actions for value1
    ;;
  "value2")
    # actions for value2
    ;;
  *)
    # actions for anything else
    ;;
esac
```

### Comparison Operators
Common comparison operators for use in conditional statements include:

- `-eq`, `-ne`, `-gt`, `-ge`, `-lt`, `-le`: Numerical comparison
- `=`, `!=`: String comparison
- `-z`: Check if string is empty
- `-n`: Check if string is not empty
- `-d`, `-f`, `-e`: File existence and type

## Functions

### Defining Functions
Functions in Bash are defined using the following syntax:

```bash
my_function() {
  # function body
}
```

You can also use the `function` keyword:

```bash
function my_function {
  # function body
}
```

### Calling Functions
To call a function, simply use its name:

```bash
my_function arg1 arg2
```

### Function Arguments
Arguments passed to a function are accessed using the `$1`, `$2`, etc. variables:

```bash
my_function() {
  echo "Argument 1: $1"
  echo "Argument 2: $2"
}

my_function hello world
```

### Returning Values
Functions can return values using the `return` statement. The exit status of the last command executed in the function is also considered the return value.

```bash
my_function() {
  local result=$((2 + 2))
  return $result
}

my_function
echo "Result: $?"  # Output: Result: 4
```

## Error Handling

### set -e
The `set -e` option causes the script to exit immediately if any command returns a non-zero exit status.

```bash
set -e
command_that_may_fail
echo "This will not be executed if the previous command failed."
```

### set -o pipefail
The `set -o pipefail` option causes the script to exit if any command in a pipeline returns a non-zero exit status.

```bash
set -o pipefail
some_command | grep pattern || echo "grep failed"
```

### try-catch
There is no built-in try-catch syntax in Bash, but you can emulate it using a combination of commands:

```bash
try() {
  "$@"
}

catch() {
  echo "Error occurred: $?"
}

try some_command
if [ $? -ne 0 ]; then
  catch
fi
```

### Logging and Debugging
You can use the `echo` and `printf` commands to print debugging information:

```bash
echo "This is a debug message"
printf "Variable value: %s\n" "$MY_VARIABLE"
```

The `set -x` option enables bash debugging, which prints each command before executing it.

```bash
set -x
command_to_debug
set +x
```

## Signal Trapping

### Trapping Signals
You can use the `trap` command to specify a function to be executed when a signal is received by the script.

```bash
trap my_function SIGINT SIGTERM
```

This will call the `my_function` function when the script receives a SIGINT (Ctrl+C) or SIGTERM signal.

### Common Signals
Some common signals that can be trapped include:

- `SIGINT` (2): Interrupt (Ctrl+C)
- `SIGTERM` (15): Terminate
- `SIGHUP` (1): Hangup
- `SIGQUIT` (3): Quit
- `SIGCHLD` (17): Child process

### Cleaning Up
Signal trapping is often used to perform cleanup tasks before the script exits, such as removing temporary files or closing database connections.

```bash
cleanup() {
  rm -f /tmp/myfile.txt
  echo "Cleanup complete."
}

trap cleanup SIGINT SIGTERM
```

## Best Practices

### Shebang
Always include a shebang line at the beginning of your script to specify the interpreter:

```bash
#!/bin/bash
```

### Quoting Variables
Always quote variable expansions to avoid word splitting and globbing:

```bash
echo "Value of MY_VAR is: '$MY_VAR'"
```

### Error Checking
Check the exit status of commands and provide meaningful error messages:

```bash
if ! some_command; then
  echo "Error: some_command failed" >&2
  exit 1
fi
```

### Consistency
Use consistent naming conventions, code formatting, and style throughout your scripts.

### Commenting
Add comments to explain the purpose, functionality, and usage of your scripts.

### Shellcheck
Use the Shellcheck tool to automatically detect common bugs and anti-patterns in your scripts.

### Testing
Write and run automated tests to ensure your scripts work as expected.

### Portability
Consider portability and compatibility across different shell implementations (Bash, Zsh, Dash, etc.).