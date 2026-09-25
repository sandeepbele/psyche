# Use an official Python runtime as a parent image
FROM python:3.9

# write gunicorn install command
RUN pip install gunicorn

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

RUN chmod +x /app/entrypoint.sh


# Expose the port that the app will run on
EXPOSE 8000

# Run the command to start the app
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
#CMD ["gunicorn", "-b", "0.0.0.0:8000", "browser_fp.wsgi:application"]
ENTRYPOINT ["/app/entrypoint.sh"]