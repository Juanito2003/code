# importing the module
import tracemalloc

# code or function for which memory
# has to be monitored

def app():
  a=3
  b=4
    
  for i in range(0, 100000):
     # c=a
     # a=b
     # b=c
      a,b=b,a
      

# starting the monitoring
tracemalloc.start()

# function call
app()

# displaying the memory
print(tracemalloc.get_traced_memory())

# stopping the library
tracemalloc.stop()
